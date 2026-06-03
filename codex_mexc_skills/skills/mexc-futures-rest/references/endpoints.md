# MEXC Futures REST Endpoint Reference

Source basis: official MEXC Futures API docs checked 2026-06-01.

Use the compact catalog instead of reading a long prose reference:

```bash
python scripts/lookup.py <topic>
```

## Auth Summary

- Base URL: `https://api.mexc.com`
- Public: no authentication.
- Private: `ApiKey`, `Request-Time`, `Signature`, optional `Recv-Window`.
- Signature target: `accessKey + timestamp + parameterString`; GET/DELETE params are sorted, POST signs compact JSON.

## Topics

`market`, `account`, `positions`, `orders`, `plan`

## Implementation Notes

- Pass signed business parameters through `--params`; do not embed query strings in signed paths.
- Verify contract detail, precision, leverage limits, and availability before live orders.
- Use exact decimal strings and prefer `externalOid` for live order idempotency.
- MEXC is live-only; respect place-order limits and back off on errors.
- Current docs moved Futures REST access to `https://api.mexc.com`; keep WebSocket code on the WebSocket base from the WebSocket skill.
