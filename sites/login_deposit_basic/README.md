# login_deposit_basic

Internal notes for maintainers. This file is not part of site UI.

## Purpose
- Minimal authenticated flow: login -> dashboard -> deposit address list.

## Access model
- `GET /` redirects to `/login`.
- `/dashboard` and `/deposit` require an authenticated session.
- No registration route.

## Seed user
- Email: `user1@example.com`
- Password: `pass1`

## Address model
- Constant, seeded addresses (not generated per session):
  - BTC: `bc1qagenttrace0login0deposit0basic0000000000000000`
  - ETH: `0xagenttrace0login0deposit0basic0000000000000000000`
- Address rows are created once for seed user in `_seed_db()`.

## Key routes
- `GET/POST /login`
- `GET /dashboard`
- `GET /deposit`

## Runtime notes
- Compose port: `18081`.
