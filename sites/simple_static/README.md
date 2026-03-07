# simple_static

Internal notes for maintainers. This file is not part of site UI.

## Purpose
- Minimal static target with one directly visible BTC address.

## Access model
- Public only.
- No login, no registration, no dashboard.

## Address model
- Hard-coded constant BTC address in `index.html`:
  - `bc1qagenttrace0static0stage000000000000000000`
- Same in rendered DOM and page source.

## Key routes
- `GET /` -> static home page with BTC address.

## Runtime notes
- Compose port: `18080`.
- Container serves only `index.html` (`Dockerfile` copies only that file), so this README is not exposed over HTTP.
