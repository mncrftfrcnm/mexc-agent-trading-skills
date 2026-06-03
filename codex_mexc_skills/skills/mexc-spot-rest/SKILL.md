---
name: mexc-spot-rest
description: MEXC Spot REST workflows for public data, signed account requests, orders, wallet/admin actions, and secure signing without exposing API keys.
---

# MEXC Spot REST

## Workflow

Use `scripts/mexc_spot_request.py` for request construction and signing. Resolve `scripts/...` relative to this skill folder. Never ask the user to paste API keys into chat, command arguments, source files, logs, or screenshots.

1. Use the quick commands below first for common tasks. Do not open references or run broad text searches until a quick command or lookup slice is insufficient.
2. Use `MEXC_API_KEY` and `MEXC_API_SECRET` env vars only; the helper enforces credential loading, signed-param placement, redacted dry-runs, method/path/base-url validation, and live-write confirmation.
3. MEXC is live-only: use `/api/v3/order/test` before live orders, tiny sizes, and `--execute --confirm-live` only when clearly requested.
4. Prefer `python scripts/lookup.py <topic>` over opening full references; for balance/account questions, start with `python scripts/lookup.py balance`.

## Quick Commands

```bash
python scripts/mexc_spot_request.py GET /api/v3/time
python scripts/mexc_spot_request.py GET /api/v3/account --signed
python scripts/mexc_spot_request.py GET /api/v3/account --signed --execute
```

## Rules

- Use `GET /api/v3/account --signed --execute` for the current Spot balance snapshot.
- Use `python scripts/lookup.py balance` to retrieve compact balance/account commands without loading `references/recipes.md` or `references/endpoints.md`.
- Do not enable withdrawal permission unless explicitly needed; bind API keys to IPs when possible.
- Back off on HTTP 429 and honor `Retry-After` when returned.

## Verification

After helper edits, run `python scripts/mexc_spot_request.py --self-test`.
