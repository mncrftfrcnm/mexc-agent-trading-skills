#!/usr/bin/env python3
"""Credential-free live smoke tests for public MEXC Spot and Futures endpoints."""

from __future__ import annotations

import argparse
import json
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Any

USER_AGENT = "mexc-agent-trading-skills-public-smoke/1.0"
SPOT_BASE = "https://api.mexc.com"
FUTURES_BASE = "https://contract.mexc.com"


def fetch_json(url: str, *, timeout: float = 15.0) -> Any:
    request = urllib.request.Request(
        url,
        headers={"Accept": "application/json", "User-Agent": USER_AGENT},
        method="GET",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            status = int(response.status)
            body = response.read().decode("utf-8", errors="strict")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"HTTP {exc.code} from {urllib.parse.urlsplit(url).netloc}: {body[:200]}") from exc
    except urllib.error.URLError as exc:
        raise RuntimeError(f"Network error from {urllib.parse.urlsplit(url).netloc}: {exc.reason}") from exc
    if status != 200:
        raise RuntimeError(f"Unexpected HTTP {status} from {urllib.parse.urlsplit(url).netloc}")
    try:
        return json.loads(body)
    except json.JSONDecodeError as exc:
        raise RuntimeError(f"Non-JSON response from {urllib.parse.urlsplit(url).netloc}") from exc


def check_spot_ping() -> None:
    value = fetch_json(f"{SPOT_BASE}/api/v3/ping")
    if not isinstance(value, dict):
        raise AssertionError("Spot ping response must be a JSON object")


def check_spot_time() -> None:
    value = fetch_json(f"{SPOT_BASE}/api/v3/time")
    if not isinstance(value, dict) or not isinstance(value.get("serverTime"), int):
        raise AssertionError("Spot time response is missing integer serverTime")


def check_futures_ping() -> None:
    value = fetch_json(f"{FUTURES_BASE}/api/v1/contract/ping")
    if not isinstance(value, dict) or value.get("success") is not True:
        raise AssertionError("Futures ping did not return success=true")
    if not isinstance(value.get("data"), int):
        raise AssertionError("Futures ping response is missing integer data timestamp")


def check_futures_ticker() -> None:
    query = urllib.parse.urlencode({"symbol": "BTC_USDT"})
    value = fetch_json(f"{FUTURES_BASE}/api/v1/contract/ticker?{query}")
    if not isinstance(value, dict) or value.get("success") is not True:
        raise AssertionError("Futures ticker did not return success=true")
    data = value.get("data")
    if not isinstance(data, dict) or data.get("symbol") != "BTC_USDT":
        raise AssertionError("Futures ticker response did not describe BTC_USDT")


def check_futures_contract_detail_once() -> None:
    query = urllib.parse.urlencode({"symbol": "BTC_USDT"})
    value = fetch_json(f"{FUTURES_BASE}/api/v1/contract/detail?{query}")
    if not isinstance(value, dict) or value.get("success") is not True:
        raise AssertionError("Futures contract detail did not return success=true")
    data = value.get("data")
    records = data if isinstance(data, list) else [data]
    record = next((item for item in records if isinstance(item, dict) and item.get("symbol") == "BTC_USDT"), None)
    if record is None:
        raise AssertionError("Futures contract detail did not contain BTC_USDT")
    if "apiAllowed" not in record:
        raise AssertionError("Futures contract detail did not expose apiAllowed")


def run(iterations: int, delay: float) -> None:
    if iterations < 1 or iterations > 50:
        raise SystemExit("--iterations must be between 1 and 50")
    if delay < 0.2:
        raise SystemExit("--delay must be at least 0.2 seconds")

    check_futures_contract_detail_once()
    passed = 0
    started = time.monotonic()
    for index in range(1, iterations + 1):
        check_spot_ping()
        check_spot_time()
        check_futures_ping()
        check_futures_ticker()
        passed += 4
        print(f"iteration {index}/{iterations}: public endpoints ok", flush=True)
        if index != iterations:
            time.sleep(delay)
    elapsed = time.monotonic() - started
    print(json.dumps({"iterations": iterations, "checks_passed": passed + 1, "elapsed_seconds": round(elapsed, 3)}))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--iterations", type=int, default=10)
    parser.add_argument("--delay", type=float, default=0.3)
    args = parser.parse_args()
    run(args.iterations, args.delay)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
