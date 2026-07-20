# Groups, Bills, and Running Balances

## Decision

Do not stretch one split room into a trip-sized container. Keep the existing room domain as one
bill and introduce a group above it:

```text
Account
  -> Friends
  -> Group or trip
       -> Members
       -> Bills (existing rooms, migrated behind the API)
            -> Items
            -> Locked allocations
       -> Running balances derived from locked allocations
       -> Manual settlements that reduce balances
```

This preserves the tested receipt, claim, lock, and settlement behavior while making a weekend
trip, flat, or recurring friend group possible.

## Product behavior

### Groups and bills

- A user can create multiple groups with different friends.
- A group can hold any number of bills.
- Closing one bill does not close the group.
- Bills have independent draft, claiming, locked, and archived states.
- Payment is optional at bill completion. Unpaid shares roll into the group balance.
- A group dashboard shows total spend, amount owed to the user, amount the user owes, pending
  settlements, and cleared settlements.

### Mixed item allocation

Room-wide `equal` versus `item_wise` is too coarse. Each item needs an allocation method:

- `claimed`: one or more people claim whole quantities, as today.
- `shared_equal`: the item's total is divided equally across selected bill participants.

For a pizza and drinks bill, pizza can be `shared_equal` by AJ, Kunal, and Mira while each drink
remains `claimed`. The selection must be explicit; silently sharing with every group member would
charge people who were not present.

Store `line_items.allocation_method` and a `line_item_sharers` relation. The locked split snapshot,
not the mutable item rows, remains the source of truth after locking. Money stays in integer paise
and remainder allocation stays deterministic.

### Running balances and partial settlement

Balances should be derived from immutable locked bill allocations plus manually confirmed
settlement entries. Do not store a mutable `current_balance` as the only source of truth.

Example:

```text
Bill 1: Kunal owes AJ Rs 420
Bill 2: AJ owes Kunal Rs 120
Net:    Kunal owes AJ Rs 300
Paid:   Kunal pays Rs 200 and AJ manually confirms
Open:   Kunal owes AJ Rs 100
```

A settlement can be partial. It records payer, payee, amount in paise, group, timestamps, and the
manual states `due`, `marked_paid`, `payer_confirmed`, or `disputed`. ReceiptSplit coordinates and
records the claim; it does not process or verify the transfer.

## Persisted model

### Account and friends

- `users`: add unique normalized `username`, `display_name`, and optional `avatar_url`.
- `friend_requests`: requester, addressee, status, timestamps, and uniqueness per pair.
- `friendships`: canonical user pair and creation timestamp.
- Username lookup returns the minimum public profile required to send a request.

### Groups

- `groups`: id, owner user id, name, optional description, status, timestamps.
- `group_members`: group id, user id, role, joined at, archived at.
- `rooms`: add nullable `group_id` during migration; existing rooms remain valid.
- Group membership never replaces room capability authorization for account-free invite users until
  the account migration is complete.

### Ledger

- Locked participant totals create immutable group ledger entries.
- `group_settlements` records manual direct-payment coordination between two group members.
- A balance read model aggregates ledger debits, credits, and payer-confirmed settlements.
- Idempotency keys prevent one locked bill or confirmed settlement from being applied twice.

## Google sign-in

Use Supabase Auth with Google as the identity provider because Supabase is already the production
target. The frontend receives a Supabase access token; the backend verifies signature, issuer,
audience, expiry, and key rotation through JWKS before mapping the subject to `users`.

Do not ship the current development JWT decoder as Google login. Production auth also needs:

- OAuth callback and session restoration in the frontend;
- verified JWKS caching and refresh;
- exact issuer and audience configuration;
- username onboarding after first sign-in;
- account-owned room and group authorization tests;
- logout, expired-session, and revoked-session behavior.

## Delivery sequence

1. Per-item `claimed` and `shared_equal` allocation with focused split invariants and UI.
2. Google sign-in, username onboarding, and an account dashboard listing owned rooms.
3. Friends and group membership.
4. Multiple bills per group with derived balances.
5. Partial manual settlements, cleared history, and pending queues.
6. Migration of legacy room sessions without invalidating existing capability links.

The order matters: groups and balances should bind to stable account identities, and settlement
history must be derived from locked bill evidence rather than UI-only totals.

## Non-negotiable boundary

This expansion does not make ReceiptSplit a wallet, escrow service, payment gateway, or bank
verification product. It must not hold funds, pool funds, auto-confirm transfers, or use `verified
paid` language.
