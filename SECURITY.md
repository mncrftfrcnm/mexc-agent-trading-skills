# Security Policy

## Reporting a vulnerability

Please do not report security issues by opening a public GitHub issue.

If you discover a vulnerability, leaked credential, unsafe trading behavior, or another security-sensitive issue, contact the maintainer privately first.

Include as much detail as you safely can:

- Affected file, skill, or workflow.
- Steps to reproduce the issue.
- Potential impact.
- Whether credentials, signatures, listen keys, account data, or live trading actions may be involved.

Do not include real API keys, API secrets, signatures, listen keys, private account payloads, screenshots containing secrets, or live account data in reports.

## Credential safety

This project expects credentials to be provided through environment variables:

```env
MEXC_API_KEY=your_api_key_here
MEXC_API_SECRET=your_api_secret_here
```

Never commit real credentials. Never paste real credentials into prompts, logs, GitHub issues, pull requests, screenshots, or shared chat transcripts.

If a key is exposed:

1. Revoke it in your MEXC account immediately.
2. Create a new key only after confirming the leak is removed.
3. Review account activity and open orders.
4. Rotate any related secrets.

## Trading-risk safety

Trading with real funds is risky. Any workflow that can submit a live order should:

- Validate symbol, precision, limits, and account state first.
- Use test endpoints where available.
- Show exact order parameters before execution.
- Require explicit user confirmation before live trading actions.
- Redact secrets, signatures, listen keys, and private account data from output.

###Out of scope

The following are not permitted:

Testing with accounts you do not own or control.
Executing live trades without explicit authorization.
Attempting to access, modify, or exfiltrate another user’s account data.
Social engineering, phishing, spam, or physical attacks.
Denial-of-service testing.
Publicly disclosing an unfixed issue before the maintainer has had reasonable time to respond.


