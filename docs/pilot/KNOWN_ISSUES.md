# Known Issues For Pilot

These are acceptable for a small pilot if testers know what to expect.

## Payment And UPI

- UPI intent behavior varies by device, browser, and installed apps.
- Desktop usually needs QR or copy fallback.
- iOS deep-link behavior may be inconsistent.
- Payment confirmation is manual.
- ReceiptSplit does not verify bank transfers.
- There is no payment gateway, webhook, bank verification, wallet, escrow, refund, or fund custody.

## Testing Status

- Real-device Android UPI chooser testing is still pending.
- iPhone Safari testing is still pending unless a device is available.
- M015 local browser screenshots use mocked API responses because local Docker/Postgres was not
  available during this run.
- Full backend pytest is blocked in this environment by Docker/Testcontainers named-pipe access.
- `npm audit --json` is policy-blocked here because the command sends dependency metadata to npm.

## Automation

- Browser smoke evidence is produced with temporary Playwright/Edge automation.
- A committed browser E2E harness is still deferred.
- Local screenshot recording can fail if the browser binary or local server is unavailable.

## UX Notes To Watch

- Very long participant names may still need real-device review.
- Real restaurant lighting and network quality may expose contrast or loading-state issues that
  desktop screenshots do not.
- Visual review from the pilot group is still needed before treating the theme as final.
