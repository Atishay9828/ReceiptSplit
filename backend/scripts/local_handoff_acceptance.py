"""Exercise local Tesseract upload through review, persistence, preview, and lock."""

from __future__ import annotations

import argparse
import base64
import json
import mimetypes
from pathlib import Path
from typing import Any

import httpx


def _dev_jwt(subject: str) -> str:
    def encode(value: dict[str, str]) -> str:
        return base64.urlsafe_b64encode(
            json.dumps(value, separators=(",", ":")).encode("utf-8")
        ).decode("ascii").rstrip("=")

    return f'{encode({"alg": "none", "typ": "JWT"})}.{encode({"sub": subject})}.signature'


def _check_response(response: httpx.Response) -> Any:
    try:
        response.raise_for_status()
    except httpx.HTTPStatusError as exc:
        raise AssertionError(f"{response.status_code} {response.request.url}: {response.text}") from exc
    return response.json()


def _run_case(
    client: httpx.Client,
    fixture: str,
    expected_total: int,
    override_amount_paise: int = 0,
    image_path: Path | None = None,
    expected_tax_paise: int | None = None,
    expected_items: list[tuple[str, int, int]] | None = None,
    expected_adjustments: list[tuple[str, int]] | None = None,
    participant_count: int = 2,
    rounding_amount_paise: int | None = None,
    rounding_delta_paise: int = 0,
) -> None:
    fixture_root = Path(__file__).resolve().parents[1] / "tests" / "fixtures" / "receipts"
    image_path = image_path or (fixture_root / "images" / f"{fixture}.png")
    content_type = mimetypes.guess_type(image_path.name)[0] or "application/octet-stream"
    created = _check_response(client.post("/api/rooms", json={"split_mode": "equal"}))
    room_id = created["room"]["id"]
    creator_headers = {"Authorization": f'Bearer {created["creator_token"]}'}

    _check_response(
        client.patch(
            f"/api/rooms/{room_id}",
            headers=creator_headers,
            json={"version": created["room"]["version"], "status": "active"},
        )
    )
    second_participant_token: str | None = None
    for index in range(1, participant_count):
        join = client.post(
            f"/api/rooms/{room_id}/join",
            headers={"Authorization": f"Bearer {_dev_jwt(f'ocr-{fixture}-guest-{index}')}"},
            json={"invite_token": created["invite_token"], "nickname": f"Guest {index}"},
        )
        joined = _check_response(join)
        if second_participant_token is None:
            second_participant_token = joined["participant_token"]

    with image_path.open("rb") as image_file:
        upload = _check_response(
            client.post(
                f"/api/rooms/{room_id}/receipts/upload",
                headers=creator_headers,
                files={"file": (image_path.name, image_file, content_type)},
            )
        )
    assert upload["provider"] == "tesseract", upload
    draft_url = f"/api/rooms/{room_id}/parsed-receipts/{upload['parsed_receipt_id']}"
    draft = _check_response(client.get(draft_url, headers=creator_headers))
    assert draft["total_paise"] == expected_total, draft
    assert draft["difference_paise"] == 0, draft
    if expected_tax_paise is not None:
        assert draft["tax_paise"] == expected_tax_paise, draft
    if expected_items is not None:
        actual_items = [
            (item["name"], item["quantity"], item["total_paise"]) for item in draft["items"]
        ]
        assert actual_items == expected_items, draft
    if expected_adjustments is not None:
        actual_adjustments = [
            (adjustment["type"], adjustment["amount_paise"])
            for adjustment in draft["adjustments"]
        ]
        assert actual_adjustments == expected_adjustments, draft

    update = {
        "merchant_name": draft["merchant_name"],
        "subtotal_paise": draft["subtotal_paise"],
        "tax_paise": draft["tax_paise"],
        "discount_paise": draft["discount_paise"],
        "total_paise": draft["total_paise"],
        "items": draft["items"],
        "adjustments": draft["adjustments"],
        "review_fingerprint": draft["review_fingerprint"],
    }
    original_rounding_amount = next(
        (row["amount_paise"] for row in update["adjustments"] if row["type"] == "rounding"),
        0,
    )
    if rounding_amount_paise is not None:
        rounding = next(
            (row for row in update["adjustments"] if row["type"] == "rounding"), None
        )
        if rounding is None:
            update["adjustments"].append(
                {"type": "rounding", "amount_paise": rounding_amount_paise, "label": "Rounding"}
            )
        else:
            rounding["amount_paise"] = rounding_amount_paise
    if rounding_delta_paise:
        update["adjustments"].append(
            {"type": "rounding", "amount_paise": rounding_delta_paise, "label": "Rounding"}
        )
    if override_amount_paise:
        item = update["items"][0]
        item["total_paise"] -= override_amount_paise
        if item["unit_price_paise"] is not None:
            item["unit_price_paise"] -= override_amount_paise
    draft = _check_response(client.patch(draft_url, headers=creator_headers, json=update))
    rounding_change = (
        rounding_amount_paise - original_rounding_amount
        if rounding_amount_paise is not None
        else 0
    )
    reviewed_total = (
        expected_total + rounding_delta_paise + rounding_change - override_amount_paise
    )
    assert draft["total_paise"] == expected_total, draft
    assert draft["calculated_total_paise"] == reviewed_total, draft
    expected_difference = rounding_delta_paise - override_amount_paise
    expected_difference += rounding_change
    assert draft["difference_paise"] == expected_difference, draft

    confirmation_payload = {
        "accept_unreconciled_total": bool(expected_difference),
        "review_fingerprint": draft["review_fingerprint"],
    }
    if expected_difference:
        rejected = client.post(
            f"{draft_url}/confirm",
            headers=creator_headers,
            json={**confirmation_payload, "accept_unreconciled_total": False},
        )
        assert rejected.status_code == 409, rejected.text
    confirmed = _check_response(client.post(
        f"{draft_url}/confirm", headers=creator_headers, json=confirmation_payload
    ))
    assert confirmed["status"] == "confirmed", confirmed

    summary = _check_response(client.get(f"/api/rooms/{room_id}/summary", headers=creator_headers))
    if second_participant_token is not None:
        participant_summary = _check_response(
            client.get(
                f"/api/rooms/{room_id}/summary",
                headers={"Authorization": f"Bearer {second_participant_token}"},
            )
        )
        assert participant_summary["room"]["id"] == room_id, participant_summary
        assert [item["total_paise"] for item in participant_summary["items"]] == [
            item["total_paise"] for item in summary["items"]
        ], participant_summary
        assert [row["amount_paise"] for row in participant_summary["adjustments"]] == [
            row["amount_paise"] for row in summary["adjustments"]
        ], participant_summary
    item_subtotal = sum(item["total_paise"] for item in summary["items"])
    assert item_subtotal == draft["subtotal_paise"] - override_amount_paise, summary
    preview = _check_response(
        client.get(f"/api/rooms/{room_id}/split/preview", headers=creator_headers)
    )
    assert preview["grand_total_paise"] == reviewed_total, preview
    assert len(preview["participant_totals"]) == participant_count, preview
    assert sum(participant["total_paise"] for participant in preview["participant_totals"]) == reviewed_total
    shares = sorted(participant["total_paise"] for participant in preview["participant_totals"])
    assert shares[-1] - shares[0] <= 1, preview

    room = _check_response(client.get(f"/api/rooms/{room_id}", headers=creator_headers))
    locked = _check_response(
        client.post(
            f"/api/rooms/{room_id}/split/lock",
            headers=creator_headers,
            json={"version": room["version"]},
        )
    )
    assert locked["grand_total_paise"] == reviewed_total, locked
    persisted = _check_response(client.get(f"/api/rooms/{room_id}/split/session", headers=creator_headers))
    assert persisted["session"]["grand_total_paise"] == reviewed_total, persisted
    print(
        json.dumps(
            {
                "fixture": fixture,
                "provider": upload["provider"],
                "receipt_total_paise": expected_total,
                "reviewed_total_paise": reviewed_total,
                "participant_count": len(preview["participant_totals"]),
                "second_participant_view": second_participant_token is None or "PASS",
                "locked_total_paise": locked["grand_total_paise"],
                "result": "PASS",
            }
        )
    )


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    args = parser.parse_args()
    repo_root = Path(__file__).resolve().parents[2]
    with httpx.Client(base_url=args.base_url, timeout=100) as client:
        health = _check_response(client.get("/health"))
        assert health["ocr_provider"] == "tesseract" and health["ocr_ready"] == "true", health
        _run_case(client, "sample_restaurant_expected", 78750)
        _run_case(
            client,
            "sample_restaurant_photo",
            78750,
            image_path=repo_root / "docs/reports/screenshots/M011.1/sample-receipt.jpg",
            expected_tax_paise=3750,
            expected_items=[
                ("Butter Chicken", 1, 35000),
                ("Garlic Naan", 2, 12000),
                ("Dal Tadka", 1, 18000),
                ("Lassi", 2, 10000),
            ],
            expected_adjustments=[("tax", 3750)],
        )
        _run_case(
            client,
            "riverside_bistro_photo",
            17348,
            image_path=repo_root / "frontend/public/assets/receipt-riverside.png",
            expected_tax_paise=1359,
            expected_items=[
                ("French Onion Soup", 1, 850),
                ("Burrata Salad", 1, 1400),
                ("Seared Scallops", 2, 3600),
                ("Herb Risotto", 1, 1850),
                ("Grilled Salmon", 1, 2400),
                ("Sautéed Green Beans", 1, 650),
                ("Lemonade", 2, 700),
                ("Pinot Noir", 1, 1200),
                ("Chocolate Torte", 1, 900),
            ],
            expected_adjustments=[("tax", 1359), ("service_charge", 2439)],
        )
        _run_case(client, "discount_rounding", 22050)
        _run_case(
            client,
            "discount_rounding",
            22050,
            rounding_amount_paise=-50,
        )
        _run_case(
            client,
            "sample_restaurant_expected",
            78750,
            participant_count=3,
            rounding_delta_paise=1,
        )
        _run_case(client, "sample_restaurant_expected", 78750, override_amount_paise=100)


if __name__ == "__main__":
    main()
