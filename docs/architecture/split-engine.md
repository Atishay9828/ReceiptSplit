# Split Engine Architecture

## Money Model

The split engine uses integer paise only. Frontend rupee and percentage inputs are converted before
they enter backend calculation.

## Adjustment Polarity

Adjustment sign is backend-owned:

- Additive: `tax`, `service_charge`, `delivery_fee`, `packaging_fee`, `tip`
- Subtractive: `discount`, `coupon`, `offer`
- Signed/manual: `adjustment`, `rounding`

Discount-like adjustments are stored and calculated as positive magnitudes, then subtracted by the
calculator. A frontend payload such as `type=discount, amount_paise=10000` means subtract INR 100.
Legacy negative discount rows are normalized at the split-input boundary so they also subtract.

## Percentage Policy

Percentage adjustments use `rate_basis_points`:

- `500` = 5%
- `1000` = 10%
- `1250` = 12.5%

For M015.1, the percentage amount is derived from the item subtotal before allocation:

1. Compute item subtotal.
2. Convert percentage charges from item subtotal.
3. Convert percentage discounts from item subtotal.
4. Allocate discounts, then additive charges, using the existing deterministic allocation methods.
5. Apply signed generic adjustments and rounding last through the existing residual policy.

Examples:

- INR 500 item subtotal + INR 100 discount = INR 400.
- INR 500 item subtotal + INR 50 tax - INR 100 discount = INR 450.
- INR 500 item subtotal + 10% discount = INR 450.
- INR 500 item subtotal + 5% tax - 10% discount = INR 475.

Discounts are capped so payable totals do not go negative.

