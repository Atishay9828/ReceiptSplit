# M012 Screenshot Evidence

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

Screenshot evidence was captured on 2026-07-07 and 2026-07-08 using local demo data and the fake VPA
`receiptsplit.test@upi`.

Captured:

- `creator-payer-setup.png`
- `settlement-prepared.png`
- `participant-pay-card.png`
- `payment-opened-upi-link.png`
- `participant-claimed-paid.png`
- `creator-confirm-payment.png`
- `payer-confirmed.png`
- `disputed-payment.png`

Notes:

- The disputed screenshot was captured on 2026-07-08 with a temporary local Postgres container on
  `127.0.0.1:55432`, backend on `127.0.0.1:8000`, frontend on `localhost:3000`, and local headless
  Chrome.
- `npm.cmd audit --json` remains unverified: the sandboxed retry failed at the npm registry
  endpoint, and the escalated retry was rejected because it sends dependency metadata to the public
  npm registry.

Demo VPA to use when smoke is rerun:

```text
receiptsplit.test@upi
```

Do not use a real UPI ID in screenshots.
