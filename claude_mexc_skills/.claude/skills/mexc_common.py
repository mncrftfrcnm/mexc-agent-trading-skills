"""Shared validation and redaction helpers for local MEXC tools."""

from __future__ import annotations

import json
import os
import urllib.parse
from typing import Any, Iterable


ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}
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


def is_authenticated_mutation(
    method: str,
    path: str,
    authenticated: bool,
    *,
    safe_path_suffixes: Iterable[str] = (),
) -> bool:
    return (
        authenticated
        and method != "GET"
        and not any(path.endswith(suffix) for suffix in safe_path_suffixes)
    )


def validate_live_execution(
    *,
    execute: bool,
    confirm_live: bool,
    method: str,
    path: str,
    authenticated: bool,
    safe_path_suffixes: Iterable[str] = (),
) -> None:
    if confirm_live and not execute:
        raise SystemExit("--confirm-live is only valid with --execute.")
    if (
        execute
        and is_authenticated_mutation(
            method,
            path,
            authenticated,
            safe_path_suffixes=safe_path_suffixes,
        )
        and not confirm_live
    ):
        raise SystemExit("Refusing live authenticated non-GET request without --confirm-live")


def redact_headers(headers: dict[str, str], sensitive_keys: Iterable[str]) -> dict[str, str]:
    sensitive = {normalize_sensitive_key(key) for key in sensitive_keys}
    return {
        key: "<redacted>" if normalize_sensitive_key(key) in sensitive else value
        for key, value in headers.items()
    }


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


def redact_json_value(
    value: Any,
    sensitive_keys: Iterable[str] = DEFAULT_SENSITIVE_KEYS,
) -> Any:
    sensitive = {normalize_sensitive_key(key) for key in sensitive_keys}
    if isinstance(value, dict):
        return {
            str(key): (
                "<redacted>"
                if normalize_sensitive_key(str(key)) in sensitive
                and item not in (None, "", [], {})
                else redact_json_value(item, sensitive)
            )
            for key, item in value.items()
        }
    if isinstance(value, list):
        return [redact_json_value(item, sensitive) for item in value]
    return value


def redact_json_text(
    text: str,
    sensitive_keys: Iterable[str] = DEFAULT_SENSITIVE_KEYS,
) -> str:
    if not text:
        return text
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        return "<redacted non-JSON payload>"
    return json.dumps(
        redact_json_value(value, sensitive_keys),
        ensure_ascii=True,
        separators=(",", ":"),
    )


def format_http_response(
    text: str,
    *,
    status: int,
    authenticated: bool,
    show_private_response: bool,
) -> str:
    if not authenticated:
        return text
    if show_private_response:
        return redact_json_text(text)

    summary: dict[str, Any] = {
        "private_response": True,
        "http_status": status,
    }
    try:
        value = json.loads(text)
    except json.JSONDecodeError:
        summary.update({"type": "text", "bytes": len(text.encode("utf-8"))})
    else:
        if isinstance(value, dict):
            summary["type"] = "object"
            summary["field_count"] = len(value)
            collection_sizes = [
                len(item)
                for item in value.values()
                if isinstance(item, (dict, list))
            ]
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
