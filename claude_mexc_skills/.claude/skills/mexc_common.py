"""Shared validation, redaction, and live-confirmation helpers for MEXC tools."""

from __future__ import annotations

import hashlib
import hmac
import json
import os
import secrets
import time
import urllib.parse
from pathlib import Path
from typing import Any, Iterable


ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
CONFIRMATION_TTL_SECONDS = 60
CONFIRMATION_DIR_ENV = "MEXC_CONFIRMATION_DIR"
DEFAULT_SENSITIVE_KEYS = frozenset(
    {
        "accesskey", "account", "accountid", "address", "apikey", "authorization",
        "clientorderid", "depositaddress", "email", "externaloid", "fromaccount",
        "invitecode", "ip", "listenkey", "memo", "orderid", "passphrase",
        "password", "phone", "privatekey", "refercode", "secret", "secretkey",
        "signature", "subaccount", "tag", "toaccount", "token", "transactionid",
        "txid", "uid", "userid", "walletaddress", "withdrawaddress",
    }
)


def strip_wrapping_quotes(value: str) -> str:
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {"'", '"'}:
        return value[1:-1]
    return value


def read_required_env(name: str) -> str:
    value = os.environ.get(name)
    if value is None:
        raise SystemExit(f"Missing env credential. Set {name}.")
    value = strip_wrapping_quotes(value).strip()
    if not value:
        raise SystemExit(f"Missing env credential. Set {name} to a non-empty value.")
    if any(ch in value for ch in "\r\n"):
        raise SystemExit(f"Refusing {name}: credential contains a newline.")
    return value


def read_mexc_api_key() -> str:
    return read_required_env("MEXC_API_KEY")


def read_mexc_credentials() -> tuple[str, str]:
    return read_required_env("MEXC_API_KEY"), read_required_env("MEXC_API_SECRET")


def load_json_params(raw: str | None, *, allow_array: bool = False) -> Any:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit(f"--params must be valid JSON: {exc}") from exc
    if isinstance(value, dict):
        return {str(k): v for k, v in value.items() if v is not None}
    if allow_array and isinstance(value, list):
        return value
    expected = "a JSON object or array" if allow_array else "a JSON object"
    raise SystemExit(f"--params must be {expected}")


def normalize_method(method: str) -> str:
    normalized = method.upper()
    if normalized not in ALLOWED_METHODS:
        choices = ", ".join(sorted(ALLOWED_METHODS))
        raise SystemExit(f"Unsupported HTTP method {method!r}. Use one of: {choices}.")
    return normalized


def normalize_path(path: str) -> str:
    stripped = path.strip()
    if not stripped:
        raise SystemExit("API path cannot be empty.")
    if "://" in stripped or stripped.startswith("//"):
        raise SystemExit("Pass only an API path, not a full URL.")
    if any(ch in stripped for ch in "\r\n\t "):
        raise SystemExit("API path cannot contain whitespace or control characters.")
    normalized = stripped if stripped.startswith("/") else f"/{stripped}"
    if not normalized.startswith("/api/"):
        raise SystemExit("API path must start with /api/.")
    return normalized


def validate_base_url(
    base_url: str,
    *,
    authenticated: bool = False,
    allowed_authenticated_hosts: Iterable[str] = (),
) -> str:
    parsed = urllib.parse.urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SystemExit("--base-url must be an absolute http(s) URL.")
    if parsed.username or parsed.password:
        raise SystemExit("--base-url must not contain embedded credentials.")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise SystemExit("--base-url must not include a path, query string, or fragment.")
    host = (parsed.hostname or "").lower()
    if parsed.scheme != "https" and host not in LOCAL_HOSTS:
        raise SystemExit("--base-url must use https unless it targets localhost.")
    if authenticated:
        allowed = {item.lower() for item in allowed_authenticated_hosts}
        if parsed.scheme != "https" or host not in allowed or parsed.port not in {None, 443}:
            choices = ", ".join(sorted(allowed))
            raise SystemExit(
                "Refusing to send authenticated credentials to this base URL. "
                f"Allowed host(s): {choices}."
            )
    return base_url.rstrip("/")


def ensure_no_signed_query(path: str, signed: bool) -> None:
    if signed and "?" in path:
        raise SystemExit(
            "For signed requests, pass business parameters through --params "
            "instead of embedding a query string in the path."
        )


def _normalized_safe_requests(
    safe_requests: Iterable[tuple[str, str]],
) -> set[tuple[str, str]]:
    return {(normalize_method(method), normalize_path(path)) for method, path in safe_requests}


def is_authenticated_mutation(
    method: str,
    path: str,
    authenticated: bool,
    *,
    safe_requests: Iterable[tuple[str, str]] = (),
) -> bool:
    normalized_method = normalize_method(method)
    normalized_path = normalize_path(path)
    return (
        authenticated
        and normalized_method != "GET"
        and (normalized_method, normalized_path) not in _normalized_safe_requests(safe_requests)
    )


def _confirmation_directory() -> Path:
    configured = os.environ.get(CONFIRMATION_DIR_ENV)
    root = (
        Path(configured).expanduser()
        if configured
        else Path.home() / ".mexc-agent-trading-skills" / "confirmations"
    )
    root.mkdir(parents=True, exist_ok=True)
    try:
        root.chmod(0o700)
    except OSError:
        pass
    return root


def _canonical_confirmation_request(method: str, path: str, params: Any) -> dict[str, Any]:
    return {"method": normalize_method(method), "path": normalize_path(path), "params": params}


def _confirmation_digest(record: dict[str, Any]) -> str:
    canonical = json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True)
    return hashlib.sha256(("mexc-live-confirmation-v1\n" + canonical).encode("utf-8")).hexdigest()


def _receipt_path(digest: str) -> Path:
    if len(digest) != 64 or any(ch not in "0123456789abcdef" for ch in digest):
        raise SystemExit("Invalid --confirm-live digest.")
    return _confirmation_directory() / f"{digest}.json"


def _remove_expired_receipts(now: int) -> None:
    root = _confirmation_directory()
    for candidate in root.glob("*.json"):
        try:
            value = json.loads(candidate.read_text(encoding="utf-8"))
            expires_at = int(value.get("expires_at", 0))
        except (OSError, ValueError, TypeError, json.JSONDecodeError):
            continue
        if expires_at < now:
            try:
                candidate.unlink()
            except OSError:
                pass


def prepare_live_confirmation(
    *, method: str, path: str, params: Any, authenticated: bool,
    safe_requests: Iterable[tuple[str, str]] = (),
    ttl_seconds: int = CONFIRMATION_TTL_SECONDS,
) -> dict[str, Any]:
    if ttl_seconds < 1 or ttl_seconds > 300:
        raise SystemExit("Confirmation TTL must be between 1 and 300 seconds.")
    if not is_authenticated_mutation(method, path, authenticated, safe_requests=safe_requests):
        raise SystemExit("--prepare-live is only valid for authenticated state-changing requests.")
    now = int(time.time())
    _remove_expired_receipts(now)
    request = _canonical_confirmation_request(method, path, params)
    record: dict[str, Any] = {
        "version": 1, **request, "nonce": secrets.token_hex(16),
        "created_at": now, "expires_at": now + ttl_seconds,
    }
    digest = _confirmation_digest(record)
    target = _receipt_path(digest)
    flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    fd = os.open(target, flags, 0o600)
    try:
        os.write(fd, json.dumps(record, sort_keys=True, separators=(",", ":"), ensure_ascii=True).encode("utf-8"))
    finally:
        os.close(fd)
    return {"live_confirmation": digest, "expires_at": record["expires_at"], "ttl_seconds": ttl_seconds, "request": request}


def consume_live_confirmation(digest: str, *, method: str, path: str, params: Any) -> None:
    target = _receipt_path(digest)
    flags = os.O_RDONLY
    if hasattr(os, "O_NOFOLLOW"):
        flags |= os.O_NOFOLLOW
    try:
        fd = os.open(target, flags)
    except FileNotFoundError as exc:
        raise SystemExit("Live confirmation is missing, expired, or already used.") from exc
    try:
        raw = os.read(fd, 1024 * 1024).decode("utf-8")
    finally:
        os.close(fd)
    try:
        record = json.loads(raw)
    except json.JSONDecodeError as exc:
        raise SystemExit("Live confirmation receipt is invalid.") from exc
    if not isinstance(record, dict) or record.get("version") != 1:
        raise SystemExit("Live confirmation receipt is invalid.")
    if not hmac.compare_digest(_confirmation_digest(record), digest):
        raise SystemExit("Live confirmation receipt failed integrity validation.")
    try:
        expires_at = int(record["expires_at"])
    except (KeyError, TypeError, ValueError) as exc:
        raise SystemExit("Live confirmation receipt is invalid.") from exc
    if expires_at < int(time.time()):
        try:
            target.unlink()
        except OSError:
            pass
        raise SystemExit("Live confirmation expired. Prepare the request again.")
    actual_request = _canonical_confirmation_request(method, path, params)
    recorded_request = {"method": record.get("method"), "path": record.get("path"), "params": record.get("params")}
    if actual_request != recorded_request:
        raise SystemExit("Live request does not match the transaction that was confirmed.")
    try:
        target.unlink()
    except FileNotFoundError as exc:
        raise SystemExit("Live confirmation was already consumed.") from exc


def validate_live_execution(
    *, execute: bool, confirm_live: str | None, method: str, path: str,
    params: Any, authenticated: bool,
    safe_requests: Iterable[tuple[str, str]] = (),
) -> None:
    mutation = is_authenticated_mutation(method, path, authenticated, safe_requests=safe_requests)
    if confirm_live and not execute:
        raise SystemExit("--confirm-live is only valid with --execute.")
    if confirm_live and not mutation:
        raise SystemExit("--confirm-live is only valid for authenticated state-changing requests.")
    if execute and mutation:
        if not confirm_live:
            raise SystemExit(
                "Refusing live authenticated state-changing request. "
                "Run --prepare-live first, review the exact transaction, then pass its digest with --confirm-live."
            )
        consume_live_confirmation(confirm_live, method=method, path=path, params=params)


def redact_headers(headers: dict[str, str], sensitive_keys: Iterable[str]) -> dict[str, str]:
    sensitive = {normalize_sensitive_key(key) for key in sensitive_keys}
    return {key: "<redacted>" if normalize_sensitive_key(key) in sensitive else value for key, value in headers.items()}


def normalize_sensitive_key(key: str) -> str:
    return "".join(ch for ch in key.lower() if ch.isalnum())


def redact_query_params(text: str, sensitive_keys: Iterable[str]) -> str:
    parsed = urllib.parse.parse_qsl(text, keep_blank_values=True)
    if not parsed:
        return text
    sensitive = {normalize_sensitive_key(key) for key in sensitive_keys}
    parts = []
    for key, value in parsed:
        encoded_key = urllib.parse.quote_plus(key)
        if normalize_sensitive_key(key) in sensitive:
            parts.append(f"{encoded_key}=<redacted>")
        else:
            parts.append(f"{encoded_key}={urllib.parse.quote_plus(value)}")
    return "&".join(parts)


def redact_json_value(value: Any, sensitive_keys: Iterable[str] = DEFAULT_SENSITIVE_KEYS) -> Any:
    sensitive = {normalize_sensitive_key(key) for key in sensitive_keys}
    if isinstance(value, dict):
        return {
            str(key): (
                "<redacted>" if normalize_sensitive_key(str(key)) in sensitive and item not in (None, "", [], {})
                else redact_json_value(item, sensitive)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_json_value(item, sensitive) for item in value]
    return value


def redact_json_text(text: str, sensitive_keys: Iterable[str] = DEFAULT_SENSITIVE_KEYS) -> str:
    if not text:
        return text
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return "<redacted non-JSON payload>"
    return json.dumps(redact_json_value(value, sensitive_keys), ensure_ascii=True, separators=(",", ":"))


def format_http_response(text: str, *, status: int, authenticated: bool, show_private_response: bool) -> str:
    if not authenticated:
        return text
    if show_private_response:
        return redact_json_text(text)
    summary: dict[str, Any] = {"private_response": True, "http_status": status}
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        summary.update({"type": "text", "bytes": len(text.encode("utf-8"))})
    else:
        if isinstance(value, dict):
            summary["type"] = "object"
            summary["field_count"] = len(value)
            collection_sizes = [len(item) for item in value.values() if isinstance(item, (dict, list))]
            if collection_sizes:
                summary["collection_sizes"] = collection_sizes
            for key in ("success", "code"):
                item = value.get(key)
                if isinstance(item, (bool, int, float)) or item is None:
                    summary[key] = item
        elif isinstance(value, list):
            summary.update({"type": "list", "count": len(value)})
        else:
            summary["type"] = type(value).__name__
    return json.dumps(summary, indent=2, ensure_ascii=True)
