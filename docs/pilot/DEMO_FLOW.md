# Pilot Demo Flow

Use fake pilot data only. The fake VPA is:

```text
receiptsplit.test@upi
```

## Scenario

1. Create room as AJ.
2. Set payer display name to AJ.
3. Set payer UPI ID to `receiptsplit.test@upi`.
4. Add Cold Coffee, quantity 3, total INR 360.
5. Add Paneer Tikka, quantity 1, total INR 240.
6. Add Masala Dosa, quantity 1, total INR 180.
7. Open claiming.
8. Join as Kunal.
9. Join as SHV_BOLT.
10. Creator claims 1 Cold Coffee.
11. Kunal claims 2 Cold Coffee.
12. SHV_BOLT claims Paneer Tikka.
13. Confirm quantity remaining and claimed labels are readable.
14. Lock the split.
15. Prepare settlement.
16. Kunal opens payment card.
17. Confirm amount, payer name, UPI ID, reference, QR, and copy fallbacks are visible.
18. Kunal taps or copies payment details, then marks `I paid`.
19. Creator manually chooses `Confirm payment`.
20. Repeat for remaining requests if present.
21. Confirm room reaches settled after all requests are payer confirmed.

## Expected Product Boundary

ReceiptSplit coordinates the request only. It does not verify transfer completion, hold funds,
process a payment, or auto-confirm payment.

## Debug Details To Record

- Short room id shown in URL or support note.
- Payment reference.
- Approximate timestamp.
- Device and browser.

Do not record raw capability tokens, invite tokens, JWTs, or private storage URLs.
