# Claude Guidance

Use this file as project guidance for Claude Code, Claude Desktop, or other Claude-based agent setups that can read this repository.

## Project purpose

This repository contains MEXC API skills for agent workflows. These workflows may include public market-data calls, signed account calls, private WebSocket streams, and live trading actions.

Treat credentials, private account data, and trading actions as sensitive.

## Environment variables

Signed workflows expect credentials in environment variables:

```env
MEXC_API_KEY=your_api_key_here
MEXC_API_SECRET=your_api_secret_here
```

Do not ask users to paste real credentials into chat. Do not print credentials, signatures, listen keys, or private account payloads.

## Skill selection

- Use `mexc-spot-rest` for Spot REST, account, and order workflows.
- Use `mexc-spot-websocket` for Spot streaming workflows.
- Use `mexc-futures-rest` for Futures REST, account, order, leverage, and position workflows.
- Use `mexc-futures-websocket` for Futures streaming workflows.

Do not use Futures skills for Spot workflows. Do not use Spot skills for Futures workflows.

## Live-action rules

Before any live order or account-changing request:

1. Validate symbol or contract metadata.
2. Validate precision, minimum size, order type, and trading status.
3. Check account state and balance when signed access is required.
4. Use test endpoints where available.
5. Show the exact final request parameters with secrets and signatures redacted.
6. Wait for explicit user confirmation.
7. Submit the live request only after confirmation.
8. Report results without exposing credentials or private payloads.

## Example safe Claude prompt

```text
Read this repository as your MEXC skill guide. Use public market-data endpoints only. Summarize the endpoint, parameters, and response shape. Do not use signed endpoints and do not place orders.
```

## Example live-action prompt pattern

```text
Use mexc-futures-rest to prepare, but not submit, a Futures order. Validate contract metadata, leverage limits, precision, and account state. Show the exact request you would send, redact signatures and secrets, and wait for explicit confirmation before any live request.
```

## Public release reminder

Before making the repository public, run local secret scanning and inspect commit history:

```bash
gitleaks detect --source . --verbose
trufflehog git file://. --only-verified
```
