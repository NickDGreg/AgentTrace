# site_one

Internal notes for maintainers. This file is not part of site UI.

## Purpose
- Richer synthetic "realistic" trading site with public pages and auth-gated account/deposit panel.

## Access model
- Public pages: `/`, `/market`, `/loans`, `/ai-trading`, `/register`, `/login`.
- Auth required: `/index`, `/account`, `/account/deposit-panel`.
- `/account/deposit-panel` returns `401` when unauthenticated.

## Seed user
- Email: `user1@example.com`
- Password: `pass1`
- Seed profile name: `Golden Pilot`

## Address model
- Deterministic per user and per asset (not random per login).
- Assets/chains:
  - `USDT` -> `TRC20`
  - `USDC` -> `TRC20`
  - `BTC` -> `BTC`
  - `ETH` -> `ERC20`
- Generation function: `_generate_address(user_id, asset)` with SHA-256 seed:
  - `"{user_id}:{asset}:goldentradr"`
- Effect:
  - Same user gets the same addresses across sessions.
  - Different users get different addresses.

## Key routes for extraction tasks
- `GET /login` -> `POST /login`
- `GET /account`
- `GET /account/deposit-panel` (returns wallet addresses + QR data URIs)

## Runtime notes
- Compose port: `18083`.
