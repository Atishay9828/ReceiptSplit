from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from urllib.parse import urlencode

from app.shared.errors import DomainError


class SettlementStatus(StrEnum):
    DUE = "due"
    PAYMENT_OPENED = "payment_opened"
    CLAIMED_PAID = "claimed_paid"
    PAYER_CONFIRMED = "payer_confirmed"
    DISPUTED = "disputed"


class SettlementNotReadyError(DomainError):
    def __init__(self, message: str = "Settlement is not ready.") -> None:
        super().__init__(code="SETTLEMENT_NOT_READY", message=message)


class SettlementRequestNotFoundError(DomainError):
    def __init__(self) -> None:
        super().__init__(code="SETTLEMENT_REQUEST_NOT_FOUND", message="Settlement request not found.")


class InvalidSettlementTransitionError(DomainError):
    def __init__(self, old_status: str, new_status: str) -> None:
        super().__init__(
            code="INVALID_SETTLEMENT_TRANSITION",
            message="This settlement action is not available right now.",
            details={"from": old_status, "to": new_status},
        )


class SettlementForbiddenError(DomainError):
    def __init__(self) -> None:
        super().__init__(code="SETTLEMENT_FORBIDDEN", message="You cannot update this payment.")


class InvalidPayerDetailsError(DomainError):
    def __init__(self, message: str = "Enter valid payer UPI details.") -> None:
        super().__init__(code="INVALID_PAYER_DETAILS", message=message)


class SettlementAmountError(DomainError):
    def __init__(self) -> None:
        super().__init__(code="SETTLEMENT_AMOUNT_ERROR", message="Settlement amount must be positive.")


class RoomNotLockedOrSettlingError(DomainError):
    def __init__(self) -> None:
        super().__init__(
            code="ROOM_NOT_LOCKED_OR_SETTLING",
            message="Lock the bill before preparing settlement.",
        )


ALLOWED_SETTLEMENT_TRANSITIONS: dict[SettlementStatus, set[SettlementStatus]] = {
    SettlementStatus.DUE: {SettlementStatus.PAYMENT_OPENED, SettlementStatus.CLAIMED_PAID, SettlementStatus.DISPUTED},
    SettlementStatus.PAYMENT_OPENED: {SettlementStatus.CLAIMED_PAID, SettlementStatus.DISPUTED},
    SettlementStatus.CLAIMED_PAID: {SettlementStatus.PAYER_CONFIRMED, SettlementStatus.DISPUTED},
    SettlementStatus.DISPUTED: {
        SettlementStatus.PAYMENT_OPENED,
        SettlementStatus.CLAIMED_PAID,
        SettlementStatus.PAYER_CONFIRMED,
    },
    SettlementStatus.PAYER_CONFIRMED: set(),
}

VPA_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9._-]{1,63}@[A-Za-z][A-Za-z0-9.-]{2,63}$")
SAFE_PAYEE_NAME_PATTERN = re.compile(r"^[A-Za-z0-9 .,'&()_-]{1,80}$")


@dataclass(frozen=True, slots=True)
class SettlementLink:
    upi_uri: str
    qr_payload: str
    amount_display: str
    payee_vpa: str
    payee_name: str
    payment_reference: str


def assert_settlement_transition(old_status: SettlementStatus, new_status: SettlementStatus) -> None:
    if old_status == new_status:
        return
    if new_status not in ALLOWED_SETTLEMENT_TRANSITIONS[old_status]:
        raise InvalidSettlementTransitionError(old_status.value, new_status.value)


def validate_payer_details(payee_vpa: str, payee_name: str) -> tuple[str, str]:
    normalized_vpa = payee_vpa.strip()
    normalized_name = " ".join(payee_name.strip().split())
    if not VPA_PATTERN.fullmatch(normalized_vpa):
        raise InvalidPayerDetailsError("Enter a valid UPI ID, for example name@upi.")
    if not SAFE_PAYEE_NAME_PATTERN.fullmatch(normalized_name):
        raise InvalidPayerDetailsError("Payer display name must be 1-80 safe characters.")
    return normalized_vpa, normalized_name


def format_paise_as_rupees(amount_paise: int) -> str:
    if amount_paise <= 0:
        raise SettlementAmountError()
    rupees, paise = divmod(amount_paise, 100)
    return f"{rupees}.{paise:02d}"


class SettlementLinkBuilder:
    def build(
        self,
        *,
        payee_vpa: str,
        payee_name: str,
        amount_paise: int,
        reference: str,
    ) -> SettlementLink:
        normalized_vpa, normalized_name = validate_payer_details(payee_vpa, payee_name)
        amount_display = format_paise_as_rupees(amount_paise)
        if not reference.strip():
            raise InvalidPayerDetailsError("Payment reference is required.")
        query = urlencode(
            {
                "pa": normalized_vpa,
                "pn": normalized_name,
                "am": amount_display,
                "cu": "INR",
                "tn": f"ReceiptSplit {reference}",
                "tr": reference,
            }
        )
        upi_uri = f"upi://pay?{query}"
        return SettlementLink(
            upi_uri=upi_uri,
            qr_payload=upi_uri,
            amount_display=amount_display,
            payee_vpa=normalized_vpa,
            payee_name=normalized_name,
            payment_reference=reference,
        )

