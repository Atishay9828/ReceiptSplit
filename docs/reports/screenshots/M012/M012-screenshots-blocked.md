# M012 Screenshots Blocked

Expected screenshot paths:

- `docs/reports/screenshots/M012/creator-payer-setup.png`
- `docs/reports/screenshots/M012/settlement-prepared.png`
- `docs/reports/screenshots/M012/participant-pay-card.png`
- `docs/reports/screenshots/M012/payment-opened-upi-link.png`
- `docs/reports/screenshots/M012/participant-claimed-paid.png`
- `docs/reports/screenshots/M012/creator-confirm-payment.png`
- `docs/reports/screenshots/M012/payer-confirmed.png`
- `docs/reports/screenshots/M012/disputed-payment.png`

Status:

Screenshots were not captured in this run.

Blocker:

- The backend API integration tests and local browser smoke require local Postgres/Docker access.
- The sandboxed Testcontainers run failed with Windows named-pipe access denied.
- The escalation retry was rejected by the environment usage gate.

Demo VPA to use when smoke is rerun:

```text
receiptsplit.test@upi
```

Do not use a real UPI ID in screenshots.
