# register_basic

Internal notes for maintainers. This file is not part of site UI.

## Purpose
- Adds a visible registration flow on top of the basic login/deposit site.

## Access model
- Public landing page at `/` with Register and Sign In links.
- `/dashboard` and `/deposit` are session-gated.

## Registration behavior
- `/register` validates form fields client-side and server-side.
- `POST /register` returns a simulated success response only.
- Registration does not create a real login account in DB.

## Seed user
- Email: `user1@example.com`
- Password: `pass1`

## Address model
- Constant, seeded addresses for the seed user:
  - BTC: `bc1qagenttrace0register0basic000000000000000000`
  - ETH: `0xagenttrace0register0basic00000000000000000000000`

## Key routes
- `GET /`
- `GET/POST /register`
- `GET/POST /login`
- `GET /dashboard`
- `GET /deposit`

## Runtime notes
- Compose port: `18082`.
