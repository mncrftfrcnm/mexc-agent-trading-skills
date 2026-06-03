# Contributing

Thanks for considering a contribution.

This repository contains agent skills for MEXC API workflows. Contributions should prioritize safety, clear documentation, and credential protection.

## Ground rules

- Do not include real API keys, API secrets, signatures, listen keys, account payloads, logs, screenshots, or private trading data.
- Use placeholders such as `your_api_key_here` and `your_api_secret_here` in examples.
- Do not add examples that submit live orders without explicit user confirmation.
- Prefer public-data examples when possible.
- Keep Spot and Futures workflows clearly separated.
- Redact sensitive request fields in documentation and tests.

## Before opening a pull request

Run these checks locally when possible:

```bash
git status
git ls-files
gitleaks detect --source . --verbose
trufflehog git file://. --only-verified
```

Also manually review changed files for:

- Hard-coded credentials.
- Accidentally committed `.env` files.
- Logs or traces containing account data.
- Live order examples that lack confirmation steps.
- Incorrect Spot/Futures endpoint mixing.

## Documentation expectations

When changing a skill or workflow, update relevant documentation with:

- What the workflow does.
- Which skill should be used.
- Whether it uses public or signed endpoints.
- Required environment variables.
- Safety checks before live actions.
- Redaction expectations for secrets and private payloads.

## Pull request checklist

- [ ] No real credentials or private account data are included.
- [ ] Examples use placeholders only.
- [ ] Live trading workflows require explicit confirmation.
- [ ] Spot and Futures workflows are not mixed accidentally.
- [ ] README or skill documentation is updated when behavior changes.
- [ ] Secret scanning has been run locally.
