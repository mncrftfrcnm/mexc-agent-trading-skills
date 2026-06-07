# MEXC Agent Trading Skills
> No financial advice. AI-assisted trading can result in financial loss.
A set of skills that allow agents to interact with the MEXC trading platform through the official MEXC API.

These skills can help agents query market data, use REST and WebSocket workflows, build signed requests, check account information, test orders, and optionally submit live trading requests when valid API credentials and explicit user confirmation are provided.

Important: This project can interact with live trading APIs. Users are solely responsible for all use, including losses, account actions, credential security, and live orders. This project is not financial advice and is provided as-is with no guarantee or liability.

> Important: This project can interact with live trading APIs. Users are solely responsible for credential security, account permissions, live orders, trading decisions, and any resulting losses. The project is provided as-is, without warranty.

## Which folder do I use?

This repository includes compatibility layouts for different agent environments and GitHub workflows. Choose the one that matches the agent environment you are installing into.

### Claude / Claude Code / Claude Desktop

Use one of the Claude-ready layouts:

```text
claude_mexc_skills/.claude/skills/
claude_mexc_skills/claude/skills/

```
For claude-code prefer the .claude folder, just like in other skills. the 'claude' folder is left, because github uploads may sometimes work very bad with . files, so that's why there are two of them

```text

claude_mexc_skills/.claude/skills/mexc-spot-rest
claude_mexc_skills/.claude/skills/mexc-spot-websocket
claude_mexc_skills/.claude/skills/mexc-futures-rest
claude_mexc_skills/.claude/skills/mexc-futures-websocket
```

Claude skill instructions use `${CLAUDE_SKILL_DIR}` so bundled helper scripts can be resolved from the installed skill root.

### Codex / Codex-style repository agents

Use the Codex-ready layout:

```text
codex_mexc_skills/skills/
```

Install or reference the skill folders from there in Codex-oriented project workflows:

```text
codex_mexc_skills/skills/mexc-spot-rest
codex_mexc_skills/skills/mexc-spot-websocket
codex_mexc_skills/skills/mexc-futures-rest
codex_mexc_skills/skills/mexc-futures-websocket
```

Codex skill instructions resolve helper scripts relative to each skill folder.

### Should I copy both?

Usually, no. The two Claude folders contain the same Claude skills for compatibility: root `claude_mexc_skills/.claude/skills/` is for auto-discovery, while `claude_mexc_skills/claude/skills/` is the non-hidden compatibility copy for GitHub workflows that do not handle hidden dot-directories well. Use the Codex folder only if you are maintaining a Codex-style installation from the same checkout.

## Continuous integration


```bash
python codex_mexc_skills/skills/mexc-spot-rest/scripts/mexc_spot_request.py --self-test
python codex_mexc_skills/skills/mexc-futures-rest/scripts/mexc_futures_request.py --self-test
python -m compileall codex_mexc_skills claude_mexc_skills
gitleaks detect --source . --verbose
```

Run `trufflehog git file://. --only-verified` locally before public release as an additional history scan.

## What the Skills Allow a Model to Do

### `mexc-spot-rest`

Use this skill for one-off MEXC Spot REST API tasks.

It can help an agent:

- Query public Spot market data, server time, symbols, and exchange information
- Read signed Spot account information such as balances and account status
- Build and sign Spot REST requests using environment-variable API credentials
- Test Spot orders with `/api/v3/order/test` before live execution
- Place Spot buy/sell orders when explicitly requested and confirmed
- Look up Spot REST endpoints and compact recipes for common workflows
- Handle wallet/admin-style Spot REST actions when supported by the API
- Avoid exposing API keys, secrets, signatures, or sensitive request data

### `mexc-spot-websocket`

Use this skill for live MEXC Spot streaming workflows.

It can help an agent:

- Connect to public Spot WebSocket streams
- Subscribe to live market data such as trades, tickers, and depth updates
- Decode current public Spot stream payloads, including protobuf-based messages
- Maintain local order books using REST snapshots plus WebSocket increments
- Create and use Spot listen keys through the Spot REST skill for private streams
- Stream private Spot account and order updates when credentials are configured
- Reconnect, resubscribe, and recover safely from stream interruptions
- Protect listen keys and avoid logging temporary stream secrets

### `mexc-futures-rest`
**Futures live-order support is experimental and may not work reliably in all cases, so you should test it yourself. Any contribution is welcome!
Use this skill for one-off MEXC Futures REST API tasks.

It can help an agent:

- Query public Futures contract data, contract details, and server status
- Read signed Futures account information such as assets, balances, and positions
- Build and sign Futures REST requests using environment-variable API credentials
- Check contract metadata, precision, leverage limits, and availabil > Futures live-order support is experimental. Test carefully with small size and confirm current MEXC API behavior before using it with real funds.
- Work with order, position, leverage, and account workflows supported by the API
- Look up Futures REST endpoints and compact recipes for common workflows
- Use safer request patterns such as external order IDs and live-action confirmations

### `mexc-futures-websocket`

Use this skill for live MEXC Futures streaming workflows.

It can help an agent:

- Connect to MEXC Futures WebSocket streams
- Subscribe to public contract market streams such as deals, tickers, and depth updates
- Stream private Futures account, order, and position updates when credentials are configured
- Maintain Futures order books using REST snapshots plus WebSocket increments
- Handle ping/pong, reconnects, and idempotent resubscriptions
- Recover from sequence gaps by rebuilding from fresh REST snapshots
- Redact private authentication payloads, signatures, and account-event data
- Respect stream lifecycle, compression behavior, and rate-limit guidance

So, instead of splitting skills into a lot of smaller files, so instead the skills are grouped into four main areas to reduce duplicated context and token usage.

## Guide

After adding these skills to your chosen agent, MEXC API credentials are required for signed account, order, and private-stream actions.

You can create API keys from your MEXC account here:

https://www.mexc.com/user/openapi

Use API permissions carefully. For most trading workflows, withdrawal permissions should be disabled.

## Setting Environment Variables

These skills expect the following environment variables:

```env
MEXC_API_KEY=your_api_key_here
MEXC_API_SECRET=your_api_secret_here
```

Do not hard-code API keys or secrets inside source files. Do not paste real keys into prompts, logs, screenshots, or GitHub issues.

### Windows Command Prompt

For the current Command Prompt session:

```bat
set MEXC_API_KEY=your_api_key_here
set MEXC_API_SECRET=your_api_secret_here
```

For permanent user environment variables:

```bat
setx MEXC_API_KEY "your_api_key_here"
setx MEXC_API_SECRET "your_api_secret_here"
```

After using `setx`, close and reopen Command Prompt.

### Windows PowerShell

For the current PowerShell session:

```powershell
$env:MEXC_API_KEY="your_api_key_here"
$env:MEXC_API_SECRET="your_api_secret_here"
```

For permanent user environment variables:

```powershell
[Environment]::SetEnvironmentVariable("MEXC_API_KEY", "your_api_key_here", "User")
[Environment]::SetEnvironmentVariable("MEXC_API_SECRET", "your_api_secret_here", "User")
```

After setting permanent variables, close and reopen PowerShell.

### macOS

For the current terminal session:

```bash
export MEXC_API_KEY="your_api_key_here"
export MEXC_API_SECRET="your_api_secret_here"
```

To make the variables available in future terminal sessions, add them to your shell profile.

For zsh, which is the default shell on recent macOS versions:

```bash
nano ~/.zshrc
```

Add:

```bash
export MEXC_API_KEY="your_api_key_here"
export MEXC_API_SECRET="your_api_secret_here"
```

Then reload the profile:

```bash
source ~/.zshrc
```

For bash:

```bash
nano ~/.bash_profile
```

Add:

```bash
export MEXC_API_KEY="your_api_key_here"
export MEXC_API_SECRET="your_api_secret_here"
```

Then reload the profile:

```bash
source ~/.bash_profile
```

### Linux

For the current terminal session:

```bash
export MEXC_API_KEY="your_api_key_here"
export MEXC_API_SECRET="your_api_secret_here"
```

To make the variables available in future terminal sessions, add them to your shell profile.

For bash:

```bash
nano ~/.bashrc
```

Add:

```bash
export MEXC_API_KEY="your_api_key_here"
export MEXC_API_SECRET="your_api_secret_here"
```

Then reload the profile:

```bash
source ~/.bashrc
```

For zsh:

```bash
nano ~/.zshrc
```

Add:

```bash
export MEXC_API_KEY="your_api_key_here"
export MEXC_API_SECRET="your_api_secret_here"
```

Then reload the profile:

```bash
source ~/.zshrc
```

### `.env` File

Some local development setups can load credentials from a `.env` file.

Create a `.env` file in your local project directory:

```env
MEXC_API_KEY=your_api_key_here
MEXC_API_SECRET=your_api_secret_here
```

Make sure `.env` is included in `.gitignore`:

```gitignore
.env
```

Never commit `.env` files to GitHub.

## Example Agent Process: Buying on Spot

For a Spot buy workflow, the agent should mainly use:

- `mexc-spot-rest` for REST API calls, endpoint lookup, signed requests, account checks, test orders, and live order placement
- `mexc-spot-websocket` only if live market data, order updates, or account updates are needed

The agent should not use Futures skills for Spot buying. Futures workflows use different endpoints, symbols, leverage rules, position logic, and risk controls.

A safe Spot buy process should look like this:

1. Understand the user request, including symbol, side, order type, amount, and whether the action is test-only or live.
2. Use `mexc-spot-rest` to check Spot exchange information for the symbol.
3. Check symbol rules such as minimum order size, precision, supported order types, and trading status.
4. Use `mexc-spot-rest` to check current market data, such as ticker price or order book data.
5. Use signed Spot REST requests to verify account balance and trading permissions.
6. Prepare the order parameters.
7. Use `/api/v3/order/test` first where supported.
8. Ask the user for explicit confirmation before any live order.
9. Submit the signed live Spot order only after confirmation.
10. Verify the order result and status.
11. Optionally use `mexc-spot-websocket` to monitor live order, balance, or market updates.
12. Report the result without exposing API keys, secrets, signatures, listen keys, or private account payloads.

Example market buy parameters:

```json
{
  "symbol": "BTCUSDT",
  "side": "BUY",
  "type": "MARKET",
  "quoteOrderQty": "25"
}
```

Example limit buy parameters:

```json
{
  "symbol": "BTCUSDT",
  "side": "BUY",
  "type": "LIMIT",
  "quantity": "0.001",
  "price": "60000",
  "timeInForce": "GTC"
}
```

## Safety Notice

This project is for developer and automation workflows only. Trading with real funds is risky. No warranty is provided. Use this project entirely at your own risk.

Always:

- Test requests carefully before live use
- Verify symbols and order parameters
- Use test endpoints where available
- Start with tiny order sizes
- Disable withdrawal permissions unless absolutely required
- Use IP restrictions where possible
- Never expose API keys, API secrets, signatures, or listen keys
- Confirm every live trading action before execution

## Safety Model

This project is designed to make accidental live trading harder, but it cannot make trading safe.

By default, helpers should prefer dry-run or test workflows. Any live authenticated non-GET request that can place, cancel, modify, or otherwise affect orders, balances, positions, or account state must require explicit user intent and confirmation.

Users should:

- Create dedicated MEXC API keys for this project only.
- Disable withdrawal permissions.
- Enable IP restrictions where supported.
- Use the minimum permissions needed for the workflow.
- Start with a sub-account or account with limited funds.
- Test public-data, account-read, and test-order flows before live trading.
- Review exact symbol, side, order type, price, quantity, leverage, margin mode, and account type before confirming any live action.
- Never run live trading workflows unattended unless they have independently reviewed and accepted the risks.
- Rotate or revoke API keys immediately if they are exposed in logs, prompts, screenshots, issues, commits, or terminal history.

This project does not guarantee profitable trading, correct order execution, uninterrupted API access, protection from exchange outages, or protection from user or AI errors.

(Authors do not take any responsibility)

## Disclaimer

This project is provided as-is for educational and developer automation purposes only. It is not financial advice, investment advice, trading advice, or a recommendation to buy, sell, or hold any asset.

Trading cryptocurrency, Spot markets, Futures markets, and leveraged products involves significant risk and may result in partial or total loss of funds. Users are solely responsible for all actions taken using this software, including API requests, live orders, account access, agent behavior, trading decisions, security settings, and credential management.

The authors, contributors, and maintainers accept no responsibility or liability for any losses, damages, failed trades, incorrect orders, missed orders, API errors, account restrictions, security issues, leaked credentials, misuse, or any other consequences resulting from the use of this project.
No warranty is provided.

Use this project entirely at your own risk.
