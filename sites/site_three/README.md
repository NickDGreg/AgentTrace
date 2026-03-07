# site_three

Internal notes for maintainers. This file is not part of site UI.

## Purpose
- Titan Trade-style synthetic site with:
  - Public marketing homepage and information pages.
  - Login/register flow.
  - JS-driven logged-in dashboard and deposit workflow.

## Access model
- Public: `/`, `/about-us`, `/price`, `/information`, `/trade-view`, `/contact-us`, `/login`, `/register`.
- Login required: `/dashboard`, `/deposit`, `/wallet-overview`, `/staking`, `/live-chat`, `/trade`, `/news`, `/auto-trader`.

## Deposit behavior
- Deposit page is rendered as a JavaScript app shell (`#root` + initial JSON state).
- User flow:
  1. Choose payment method (Crypto, Amex, Card, Bank Transfer).
  2. For Crypto, enter amount + asset and click `Next`.
  3. Frontend calls `GET /api/deposit/address?asset=...&amount=...`.
  4. API returns QR + wallet address for selected asset.

## Address model
- Fixed global addresses shared by all users (not per-user):
  - BTC: `bc1qnhgc9vlhra74ay2yqlyrp5ppq9czpdylagqhq7`
  - ETH: `0x9a850f5a9f9634f8f5f0a7483d8f0f0c9cd19c2f`
  - BCH: `bitcoincash:qpm2qsznhks23z7629mms6s4cwef74vcwvy22gdx6a`

## Seed user
- Email: `user1@example.com`
- Password: `pass1`
- Display name: `john`

## Runtime notes
- Compose file: `sites/site_three/compose.yaml`
- Mapped URL: `http://localhost:18085/login`
