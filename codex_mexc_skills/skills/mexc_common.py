"""Shared validation and redaction helpers for local MEXC tools."""

from __future__ import annotations

import json
import os
import urllib.parse
from typing import Any, Iterable


ALLOWED_METHODS = {"GET", "POST", "PUT", "DELETE"}
LOCAL_HOSTS = {"localhost", "127.0.0.1", "::1"}


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


def validate_base_url(base_url: str) -> str:
    parsed = urllib.parse.urlsplit(base_url)
    if parsed.scheme not in {"http", "https"} or not parsed.netloc:
        raise SystemExit("--base-url must be an absolute http(s) URL.")
    if parsed.path not in {"", "/"} or parsed.query or parsed.fragment:
        raise SystemExit("--base-url must not include a path, query string, or fragment.")
    host = parsed.hostname or ""
    if parsed.scheme != "https" and host not in LOCAL_HOSTS:
        raise SystemExit("--base-url must use https unless it targets localhost.")
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
    sensitive = {key.lower() for key in sensitive_keys}
    return {
        key: "<redacted>" if key.lower() in sensitive else value
        for key, value in headers.items()
    }


def redact_query_params(text: str, sensitive_keys: Iterable[str]) -> str:
    parsed = urllib.parse.parse_qsl(text, keep_blank_values=True)
    if not parsed:
        return text
    sensitive = {key.lower() for key in sensitive_keys}
    parts = []
    for key, value in parsed:
        encoded_key = urllib.parse.quote_plus(key)
        if key.lower() in sensitive:
            parts.append(f"{encoded_key}=<redacted>")
        else:
            parts.append(f"{encoded_key}={urllib.parse.quote_plus(value)}")
    return "&".join(parts)
