# UPI Intent QA

ReceiptSplit generates UPI intent links and QR payloads. It does not control installed UPI apps,
browser protocol handling, or bank transfer outcomes.

## Expected Behavior

### Android Phone

- `Open UPI app` may show a chooser of installed UPI apps.
- It may open the user's default UPI app directly.
- If the browser blocks or ignores the protocol, the QR and copy fallback must remain visible.

### Desktop

- `Open UPI link` may do nothing, show an unsupported protocol prompt, or fail silently.
- Desktop users should scan the QR with a phone or copy the UPI ID/payment link into their banking
  app.
- Desktop behavior is not a ReceiptSplit payment failure.

### iOS

- UPI deep-link behavior varies by browser and installed apps.
- Safari or the selected UPI app may ignore the intent.
- QR, copy UPI ID, and copy payment link must remain visible.

## Must Not Claim

- Do not claim ReceiptSplit guarantees opening a UPI app.
- Do not claim ReceiptSplit verifies payment.
- Do not claim bank confirmation, payment verification, or payment success.

## QA Result Format

For each tested device, record:

- Device and browser.
- Installed UPI apps.
- Whether tapping the UPI button opened an app, showed a chooser, or failed.
- Whether QR scan worked.
- Whether copy UPI ID worked.
- Whether the safety notice remained visible.
