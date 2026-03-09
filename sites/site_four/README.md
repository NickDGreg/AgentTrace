# site_four

Internal notes for maintainers. This file is not part of site UI.

## Purpose
- BitradeX-style synthetic environment with:
  - Public marketing pages under `/en`.
  - Login/register flow.
  - Auth-gated wallet/deposit pages that require client-side interaction to reveal deposit addresses.

## Access model
- Public routes:
  - `/`
  - `/en`
  - `/en/aibot`
  - `/en/markets`
  - `/en/futures`
  - `/en/trade`
  - `/en/invite-friend`
  - `/en/about`
  - `/en/contact`
  - `/en/login`
  - `/en/register`
- Login required:
  - `/en/balance/overview`
  - `/en/balance/spot-account`
  - `/en/balance/deposit`
  - `/en/balance/withdraw`
  - `/en/balance/bills`
  - `/v1/*` private endpoints used by authenticated UI requests.

## Login landing
- Successful sign-in redirects to `/en/trade` (not directly to deposit).

## Deposit behavior
- Deposit page route: `/en/balance/deposit`
- UI flow mirrors a JS-heavy webapp pattern:
  1. Open asset drawer and select coin (`Asset Name`).
  2. Choose network (`Transfer Network`).
  3. Address and QR render in `Deposit Details`.
- Addresses are not present in initial HTML.
- Frontend requests include:
  - `/v1/spot/wallet/deposit/hot/coin`
  - `/v1/spot/wallet/deposit/network?coin=...`
  - `/v1/spot/wallet/deposit/address?coin=...&network=...`
  - `/v1/spot/wallet/deposit/history?page=1&size=10`
  - plus additional `/v1/...` warmup endpoints to emulate production request chains.

## Address model
- Deterministic per user, coin, and network.
- Same user sees stable addresses across sessions.
- Different users get different addresses.
- Supported deposit assets with addresses:
  - `BTC` on `BTC`
  - `ETH` on `ERC20`
  - `USDT` on `TRC20` and `ERC20`

## Seed user
- Email: `user1@example.com`
- Password: `pass1`
- Display name: `alex`

## Runtime notes
- Compose file: `sites/site_four/compose.yaml`
- Mapped URL: `http://localhost:18086/en/login`
