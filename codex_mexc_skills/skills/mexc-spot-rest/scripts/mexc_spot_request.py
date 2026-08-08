#!/usr/bin/env python3
"""Build and optionally execute secure MEXC Spot REST requests."""

from __future__ import annotations

import argparse
import hashlib
import hmac
import json
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path
from typing import Any

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))
from mexc_common import (  # noqa: E402
    DEFAULT_SENSITIVE_KEYS,
    ensure_no_signed_query,
    format_http_response,
    load_json_params,
    normalize_method,
    normalize_path,
    prepare_live_confirmation,
    read_mexc_api_key,
    read_mexc_credentials,
    redact_headers as redact_auth_headers,
    redact_query_params,
    strip_wrapping_quotes,
    validate_base_url,
    validate_live_execution,
)

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")

BASE_URL = "https://api.mexc.com"
AUTHENTICATED_HOSTS = {"api.mexc.com"}
SAFE_LIVE_REQUESTS = {("POST", "/api/v3/order/test")}
EXAMPLES = "examples: GET /api/v3/time | GET /api/v3/account --signed"
DOCS_EXAMPLE_SECRET = "45d0b3c26f2644f19bfb98b07741b2f5"
DOCS_EXAMPLE_QUERY = (
    "symbol=BTCUSDT&side=BUY&type=LIMIT&quantity=1&price=11"
    "&recvWindow=5000&timestamp=1644489390087"
)
DOCS_EXAMPLE_SIGNATURE = (
    "fd3e4e8543c5188531eb7279d68ae7d26a573d0fc5ab0d18eb692451654d837a"
)


def load_params(raw: str | None) -> dict[str, Any]:
    return load_json_params(raw, allow_array=False)


def encode_params(params: dict[str, Any]) -> str:
    return urllib.parse.urlencode(params, doseq=True)


def sign_total_params(total_params: str, secret: str) -> str:
    return hmac.new(secret.encode(), total_params.encode(), hashlib.sha256).hexdigest()


def env_api_key() -> str:
    return read_mexc_api_key()


def env_credentials() -> tuple[str, str]:
    return read_mexc_credentials()


def redact_headers(headers: dict[str, str]) -> dict[str, str]:
    return redact_auth_headers(headers, {"X-MEXC-APIKEY"})


def redact_sensitive_params(text: str) -> str:
    return redact_query_params(text, DEFAULT_SENSITIVE_KEYS)


def build_request(args: argparse.Namespace) -> tuple[str, str, dict[str, str], bytes | None, str]:
    method = normalize_method(args.method)
    path = normalize_path(args.path)
    ensure_no_signed_query(path, args.signed)
    url = validate_base_url(
        args.base_url,
        authenticated=args.signed or args.api_key_only,
        allowed_authenticated_hosts=AUTHENTICATED_HOSTS,
    ) + path
    headers = {"User-Agent": "mexc-agent-spot-helper/1.1"}
    params = load_params(args.params)
    body = None
    encoded = encode_params(params)

    if args.api_key_only:
        headers["X-MEXC-APIKEY"] = env_api_key()
    if args.signed:
        api_key, secret = env_credentials()
        params["recvWindow"] = str(args.recv_window)
        params["timestamp"] = str(args.timestamp or int(time.time() * 1000))
        encoded = encode_params(params)
        signature = sign_total_params(encoded, secret)
        encoded_with_signature = f"{encoded}&signature={signature}" if encoded else f"signature={signature}"
        headers["X-MEXC-APIKEY"] = api_key
    else:
        encoded_with_signature = encoded

    if method == "GET":
        if encoded_with_signature:
            url = f"{url}?{encoded_with_signature}"
        printable_body = ""
    else:
        headers["Content-Type"] = "application/x-www-form-urlencoded"
        body = encoded_with_signature.encode() if encoded_with_signature else None
        printable_body = encoded_with_signature
    return method, url, headers, body, printable_body


def execute(
    method: str,
    url: str,
    headers: dict[str, str],
    body: bytes | None,
    *,
    authenticated: bool,
    show_private_response: bool,
) -> int:
    request = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(request, timeout=20) as response:
            status = int(response.status)
            text = response.read().decode("utf-8", errors="replace")
            sys.stdout.write(
                format_http_response(
                    text,
                    status=status,
                    authenticated=authenticated,
                    show_private_response=show_private_response,
                )
            )
            return 0 if 200 <= status < 300 else 1
    except urllib.error.HTTPError as exc:
        text = exc.read().decode("utf-8", errors="replace")
        sys.stderr.write(
            format_http_response(
                text,
                status=int(exc.code),
                authenticated=authenticated,
                show_private_response=show_private_response,
            )
        )
        return 1
    except (urllib.error.URLError, TimeoutError):
        sys.stderr.write("Network request failed; signed URL and request details were suppressed.\n")
        return 1


def self_test() -> None:
    actual = sign_total_params(DOCS_EXAMPLE_QUERY, DOCS_EXAMPLE_SECRET)
    if actual != DOCS_EXAMPLE_SIGNATURE:
        raise SystemExit("Spot signature self-test failed")
    if strip_wrapping_quotes("'abc123'") != "abc123":
        raise SystemExit("Spot credential quote stripping self-test failed")
    print("spot self-test ok")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=__doc__,
        epilog=EXAMPLES,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument("method", nargs="?", help="HTTP method, e.g. GET or POST")
    parser.add_argument("path", nargs="?", help="API path, e.g. /api/v3/time")
    parser.add_argument("--params", help="JSON object of business parameters")
    parser.add_argument("--api-key-only", action="store_true", help="Send only X-MEXC-APIKEY from env")
    parser.add_argument("--signed", action="store_true", help="Sign request using env credentials")
    parser.add_argument("--execute", action="store_true", help="Send the request. Default is dry-run.")
    parser.add_argument(
        "--prepare-live",
        action="store_true",
        help="Create a short-lived one-time confirmation for this exact live mutation without sending it",
    )
    parser.add_argument(
        "--confirm-live",
        metavar="DIGEST",
        help="One-time digest produced by --prepare-live for this exact transaction",
    )
    parser.add_argument(
        "--show-private-response",
        action="store_true",
        help="Print a redacted private response instead of metadata only",
    )
    parser.add_argument("--recv-window", default="5000")
    parser.add_argument("--timestamp")
    parser.add_argument("--base-url", default=BASE_URL)
    parser.add_argument("--self-test", action="store_true")
    args = parser.parse_args()
    if args.self_test:
        return args
    if not args.method or not args.path:
        parser.error("method and path are required unless --self-test is used")
    if args.api_key_only and args.signed:
        parser.error("--api-key-only and --signed are mutually exclusive")
    if args.prepare_live and (args.execute or args.confirm_live):
        parser.error("--prepare-live cannot be combined with --execute or --confirm-live")
    return args


def main() -> int:
    args = parse_args()
    if args.self_test:
        self_test()
        return 0
    method = normalize_method(args.method)
    path = normalize_path(args.path)
    params = load_params(args.params)
    authenticated = args.signed or args.api_key_only
    if args.prepare_live:
        prepared = prepare_live_confirmation(
            method=method,
            path=path,
            params=params,
            authenticated=authenticated,
            safe_requests=SAFE_LIVE_REQUESTS,
        )
        print(json.dumps(prepared, indent=2, sort_keys=True))
        return 0
    validate_live_execution(
        execute=args.execute,
        confirm_live=args.confirm_live,
        method=method,
        path=path,
        params=params,
        authenticated=authenticated,
        safe_requests=SAFE_LIVE_REQUESTS,
    )
    method, url, headers, body, printable_body = build_request(args)
    if not args.execute:
        parsed_url = urllib.parse.urlsplit(url)
        safe_url = urllib.parse.urlunsplit(
            (
                parsed_url.scheme,
                parsed_url.netloc,
                parsed_url.path,
                redact_sensitive_params(parsed_url.query),
                parsed_url.fragment,
            )
        )
        print(
            json.dumps(
                {
                    "dry_run": True,
                    "method": method,
                    "url": safe_url,
                    "headers": redact_headers(headers),
                    "body": redact_sensitive_params(printable_body),
                },
                indent=2,
            )
        )
        return 0
    return execute(
        method,
        url,
        headers,
        body,
        authenticated=authenticated,
        show_private_response=args.show_private_response,
    )


if __name__ == "__main__":
    raise SystemExit(main())
