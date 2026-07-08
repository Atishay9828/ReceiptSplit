from __future__ import annotations

import pytest

from app.domain.settlement import (
    InvalidPayerDetailsError,
    InvalidSettlementTransitionError,
    SettlementAmountError,
    SettlementLinkBuilder,
    SettlementStatus,
    assert_settlement_transition,
)


def test_link_builder_formats_paise_and_encodes_upi_uri() -> None:
    link = SettlementLinkBuilder().build(
        payee_vpa="receiptsplit.test@upi",
        payee_name="AJ Payer",
        amount_paise=44600,
        reference="RS-ROOM-BOB",
    )

    assert link.amount_display == "446.00"
    assert link.upi_uri.startswith("upi://pay?")
    assert "pa=receiptsplit.test%40upi" in link.upi_uri
    assert "pn=AJ+Payer" in link.upi_uri
    assert "am=446.00" in link.upi_uri
    assert "cu=INR" in link.upi_uri
    assert "tr=RS-ROOM-BOB" in link.upi_uri
    assert link.qr_payload == link.upi_uri


@pytest.mark.parametrize("amount_paise", [0, -1])
def test_link_builder_rejects_non_positive_amounts(amount_paise: int) -> None:
    with pytest.raises(SettlementAmountError):
        SettlementLinkBuilder().build(
            payee_vpa="receiptsplit.test@upi",
            payee_name="AJ Payer",
            amount_paise=amount_paise,
            reference="RS-ROOM-BOB",
        )


@pytest.mark.parametrize("vpa", ["", "missing-at", "bad space@upi", "a@u"])
def test_link_builder_rejects_invalid_vpa(vpa: str) -> None:
    with pytest.raises(InvalidPayerDetailsError):
        SettlementLinkBuilder().build(
            payee_vpa=vpa,
            payee_name="AJ Payer",
            amount_paise=100,
            reference="RS-ROOM-BOB",
        )


def test_payer_confirmed_is_terminal() -> None:
    with pytest.raises(InvalidSettlementTransitionError):
        assert_settlement_transition(
            SettlementStatus.PAYER_CONFIRMED,
            SettlementStatus.DISPUTED,
        )
