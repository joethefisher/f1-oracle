# Workflow: Kalshi API Authentication

## Objective
Establish and verify authenticated access to the Kalshi trading API using RSA key signing.

## Required Inputs
- `KALSHI_API_KEY_ID` in `.env`
- `KALSHI_PRIVATE_KEY_PEM` in `.env` (full PEM string, newlines as `\n`)
- `KALSHI_BASE_URL` in `.env`

## Steps
1. Load env vars via `python-dotenv`
2. Run `tools/kalshi_auth_check.py` — verifies auth by calling `GET /portfolio/balance`
3. Log the response. A successful auth returns current balance.
4. If auth fails: check key ID is correct, check PEM format has no extra whitespace

## Expected Output
- Console: `Auth OK. Balance: $X.XX`
- On failure: error message with HTTP status and Kalshi error code

## Error Handling
- 401: wrong key ID or malformed signature
- 403: account not funded or not approved for trading
- 429: rate limited — wait 60s and retry once

## Notes
- Use sandbox credentials (`https://demo-api.kalshi.co/trade-api/v2`) for development
- Never log the private key — only log the key ID
- SDK: `kalshi-python` v2.1.4+
