# Real Device QA Checklist

M015 prepares this checklist for a small pilot. Do not mark an item complete until it has been
tested on the named device/browser with fake demo data only.

## Devices

- [ ] Android Chrome, small phone width.
- [ ] Android Chrome, large phone width.
- [ ] iPhone Safari if available.
- [ ] Desktop Chrome.
- [ ] Desktop Edge.

## Room Creation And Sharing

- [ ] Create a room as AJ.
- [ ] Add payer display name.
- [ ] Add fake VPA `receiptsplit.test@upi`.
- [ ] Copy invite link.
- [ ] Share invite link through WhatsApp.
- [ ] Join as Kunal.
- [ ] Join as SHV_BOLT.
- [ ] Confirm no raw invite token or capability token is shown in UI.

## Claiming Flow

- [ ] Add Cold Coffee, quantity 3, total INR 360.
- [ ] Add Paneer Tikka, quantity 1, total INR 240.
- [ ] Add Masala Dosa, quantity 1, total INR 180.
- [ ] Open claiming.
- [ ] Creator claims 1 Cold Coffee.
- [ ] Kunal claims 2 Cold Coffee.
- [ ] SHV_BOLT claims Paneer Tikka.
- [ ] Quantity remaining and claimed names are readable on mobile.
- [ ] Participant removal works before lock and releases claims.
- [ ] Removed participant cannot continue using the stale room session.

## Settlement Flow

- [ ] Lock split.
- [ ] Prepare settlement.
- [ ] Participant sees amount due, payer name, UPI ID, and reference.
- [ ] QR is readable in dark mode.
- [ ] Open UPI app remains available where supported.
- [ ] Copy UPI ID works.
- [ ] Copy payment link works.
- [ ] Mark I paid.
- [ ] Payer confirm moves status to payer confirmed.
- [ ] Payer confirmed hides payment actions.
- [ ] Room moves to settled when all requests are payer confirmed.

## Network And Error Conditions

- [ ] Slow network still shows usable loading states.
- [ ] Offline or failed refresh shows a recoverable error.
- [ ] Duplicate claim conflict gives a clear retry/refresh message.
- [ ] UPI intent failure does not hide QR or copy fallback.

## Safety And Abuse

- [ ] Safety notice is visible near payment actions.
- [ ] Abuse report opens, submits, and shows received state.
- [ ] Expired or removed participant behavior is understandable.
- [ ] UI does not say verified paid, payment verified, bank confirmed, or payment successful.

## Status

M015 local browser UI evidence was captured with mocked API responses. Real Android/iPhone UPI
chooser behavior is still pending real-device testing.
