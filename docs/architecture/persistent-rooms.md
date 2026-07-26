# Persistent Rooms and Mixed Item Splits

## Domain Model

ReceiptSplit keeps the existing `rooms` table as the bill boundary. A new `groups` aggregate is the
persistent social room the user sees on the dashboard.

```text
user -> friendships -> group_members -> group -> rooms (bills)
                                           |       |
                                           |       +-> split session and participant totals
                                           |       +-> settlement requests and status history
                                           +-> aggregated pending and cleared ledger
```

This separation avoids reopening a settled bill or merging unrelated receipts. A bill may finish;
the group remains available for the next receipt.

## Mixed Item Allocation

Every line item has one allocation mode:

- `individual`: participants claim explicit quantities;
- `equal`: the split engine allocates that line's paise across all active participants.

An item-wise bill may contain both modes. Equal items do not block claim readiness and cannot be
claimed manually. Allocation remains deterministic and conserves integer paise.

## Ledger Meaning

- `all bills`: sum of locked bill grand totals;
- `pending`: sum of locked non-payer participant totals minus all payer-confirmed amounts;
- `cleared`: sum of confirmed full or partial settlement amounts.

Opening UPI, marking paid, and payer confirmation remain manual coordinator states. ReceiptSplit
does not inspect bank transfers or claim that a payment is verified.

## Identity and Access

Google Identity Services supplies an ID token. The backend verifies its signature, issuer, and
audience with Google's verifier before upserting the local user. Unique lowercase usernames are
used for friend discovery.

Each group member is linked to a `room_participants` row for every bill in that group. A signed-in
member receives only participant-scoped bill and settlement access; ownership remains limited to
the group owner. Legacy capability-token quick bills remain supported.
