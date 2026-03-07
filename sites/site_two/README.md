# site_two

Internal notes for maintainers. This file is not part of site UI.

## Purpose
- Synthetic clone-pattern site with realistic public marketing pages plus dashboard workflows.
- Primary focus is auth + deposit/signal payment paths that expose crypto addresses.

## Access model
- Public routes: `/`, `/about`, `/contact`, `/faq`, `/register`, `/login`.
- Auth required for all `/dashboard/*` routes.

## Seed user
- Email: `user1@example.com`
- Password: `pass1`
- Display name: `john`

## Address model
- Deterministic per user and per chain.
- Chains used in deposit/signal flows:
  - `BTC`
  - `ETH`
  - `BCH`
- Generation function: `_generate_address(user_id, chain)` with SHA-256 seed:
  - `"{user_id}:{chain}:site-two"`
- `_ensure_user_addresses()` upserts expected deterministic values.
- Effect:
  - Same user sees the same BTC/ETH/BCH addresses across sign in/out sessions.
  - Different users see different addresses.

## Deposit and signal flows
- Deposit:
  - `POST /dashboard/newdeposit` -> create deposit -> redirect to `GET /dashboard/payment?deposit_id=...`
  - Payment page resolves chain from payment method and displays address + QR.
- Signal purchase:
  - `POST /dashboard/signalnewdeposit` -> create signal order -> redirect to `GET /dashboard/singnalpayment?order_id=...`
  - Route keeps source typo (`singnalpayment`) to mirror target behavior.

## Payment method to chain mapping
- `Bitcoin` -> `BTC`
- `Ethereum` -> `ETH`
- `Bitcoin Cash` -> `BCH`

## Runtime notes
- Compose port in current file: `18084`.
- This currently overlaps with `crawl_test` if both are started together.
