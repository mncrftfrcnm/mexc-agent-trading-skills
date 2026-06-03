# Agent Guidance

Use this file as operational guidance for Codex and other code agents working in this repository.

## Project purpose

This repository provides MEXC trading skills for agent workflows. The skills can involve public market data, signed account requests, private WebSocket streams, and live trading actions.

Safety is more important than speed.

## Required behavior

When working with these skills:

- Keep Spot and Futures workflows separate.
- Prefer public endpoints when credentials are not required.
- Use `MEXC_API_KEY` and `MEXC_API_SECRET` from the environment only.
- Never hard-code credentials.
- Never print credentials, signatures, listen keys, or private account payloads.
- Validate symbols, precision, limits, balances, and account state before trading actions.
- Use test endpoints where available.
- Require explicit user confirmation before any live order or account-changing request.

## Skill selection

- Use `mexc-spot-rest` for Spot REST, account, and order workflows.
- Use `mexc-spot-websocket` for Spot streaming workflows.
- Use `mexc-futures-rest` for Futures REST, account, order, leverage, and position workflows.
- Use `mexc-futures-websocket` for Futures streaming workflows.

## Codex usage pattern

Before a live action, Codex should summarize:

- Skill being used.
- Endpoint or workflow.
- Symbol or contract.
- Side, order type, quantity, price, leverage, and time-in-force when relevant.
- Whether the action is test-only or live.
- Redactions applied.

Then Codex must wait for explicit user confirmation before executing the live action.

## Example safe Codex prompt

```text
Use the MEXC skills in this repository. Check BTCUSDT Spot exchange information and ticker data only. Do not place live orders. Do not print credentials, signatures, or private account payloads.
```

## Example live-action prompt pattern

```text
Use mexc-spot-rest to prepare a BTCUSDT Spot market buy using 25 USDT. First validate symbol rules and balance, then run the test-order endpoint if available. Before any live order, show me the final parameters and wait for my explicit confirmation.
```

## Public release reminder

Before making the repository public, run a local secret scan and inspect commit history:

```bash
gitleaks detect --source . --verbose
trufflehog git file://. --only-verified
```
