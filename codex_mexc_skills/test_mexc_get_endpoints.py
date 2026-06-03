#!/usr/bin/env python3
"""Run read-only MEXC GET recipe checks and print redacted outputs."""

from __future__ import annotations

import json
import subprocess
import time
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
SPOT = ["python", "skills\\mexc-spot-rest\\scripts\\mexc_spot_request.py"]
FUTURES = ["python", "skills\\mexc-futures-rest\\scripts\\mexc_futures_request.py"]


TESTS: list[tuple[str, list[str]]] = [
    ("spot.market.ping", SPOT + ["GET", "/api/v3/ping", "--execute"]),
    ("spot.market.time", SPOT + ["GET", "/api/v3/time", "--execute"]),
    ("spot.market.defaultSymbols", SPOT + ["GET", "/api/v3/defaultSymbols", "--execute"]),
    ("spot.market.exchangeInfo", SPOT + ["GET", "/api/v3/exchangeInfo", "--execute"]),
    ("spot.market.depth.BTCUSDT", SPOT + ["GET", "/api/v3/depth", "--params", '{"symbol":"BTCUSDT","limit":20}', "--execute"]),
    ("spot.market.trades.BTCUSDT", SPOT + ["GET", "/api/v3/trades", "--params", '{"symbol":"BTCUSDT","limit":20}', "--execute"]),
    ("spot.market.aggTrades.BTCUSDT", SPOT + ["GET", "/api/v3/aggTrades", "--params", '{"symbol":"BTCUSDT","limit":20}', "--execute"]),
    ("spot.market.klines.BTCUSDT", SPOT + ["GET", "/api/v3/klines", "--params", '{"symbol":"BTCUSDT","interval":"1m","limit":5}', "--execute"]),
    ("spot.market.ticker24hr.BTCUSDT", SPOT + ["GET", "/api/v3/ticker/24hr", "--params", '{"symbol":"BTCUSDT"}', "--execute"]),
    ("spot.market.tickerPrice.BTCUSDT", SPOT + ["GET", "/api/v3/ticker/price", "--params", '{"symbol":"BTCUSDT"}', "--execute"]),
    ("spot.market.bookTicker.BTCUSDT", SPOT + ["GET", "/api/v3/ticker/bookTicker", "--params", '{"symbol":"BTCUSDT"}', "--execute"]),
    ("spot.account.balances", SPOT + ["GET", "/api/v3/account", "--signed", "--execute"]),
    ("spot.account.kyc", SPOT + ["GET", "/api/v3/kyc/status", "--signed", "--execute"]),
    ("spot.account.selfSymbols", SPOT + ["GET", "/api/v3/selfSymbols", "--signed", "--execute"]),
    ("spot.account.myTrades.BTCUSDT", SPOT + ["GET", "/api/v3/myTrades", "--signed", "--params", '{"symbol":"BTCUSDT"}', "--execute"]),
    ("spot.orders.openOrders.BTCUSDT", SPOT + ["GET", "/api/v3/openOrders", "--signed", "--params", '{"symbol":"BTCUSDT"}', "--execute"]),
    ("spot.orders.allOrders.BTCUSDT", SPOT + ["GET", "/api/v3/allOrders", "--signed", "--params", '{"symbol":"BTCUSDT"}', "--execute"]),
    ("spot.stream.listenKeys", SPOT + ["GET", "/api/v3/userDataStream", "--signed", "--execute"]),
    ("spot.wallet.currencyConfig", SPOT + ["GET", "/api/v3/capital/config/getall", "--signed", "--execute"]),
    ("spot.wallet.depositHistory.USDT", SPOT + ["GET", "/api/v3/capital/deposit/hisrec", "--signed", "--params", '{"coin":"USDT"}', "--execute"]),
    ("spot.wallet.withdrawHistory.USDT", SPOT + ["GET", "/api/v3/capital/withdraw/history", "--signed", "--params", '{"coin":"USDT"}', "--execute"]),
    ("spot.wallet.depositAddress.USDT.TRX", SPOT + ["GET", "/api/v3/capital/deposit/address", "--signed", "--params", '{"coin":"USDT","network":"TRX"}', "--execute"]),
    ("spot.subaccount.list", SPOT + ["GET", "/api/v3/sub-account/list", "--signed", "--params", '{"page":1,"limit":20}', "--execute"]),
    ("spot.subaccount.transferHistory", SPOT + ["GET", "/api/v3/capital/sub-account/universalTransfer", "--signed", "--params", '{"limit":100}', "--execute"]),
    ("spot.rebate.taxQuery", SPOT + ["GET", "/api/v3/rebate/taxQuery", "--signed", "--params", '{"page":1}', "--execute"]),
    ("spot.rebate.detail", SPOT + ["GET", "/api/v3/rebate/detail", "--signed", "--params", '{"page":1}', "--execute"]),
    ("spot.rebate.kickback", SPOT + ["GET", "/api/v3/rebate/detail/kickback", "--signed", "--params", '{"page":1}', "--execute"]),
    ("spot.rebate.referCode", SPOT + ["GET", "/api/v3/rebate/referCode", "--signed", "--execute"]),
    ("spot.rebate.affiliateReferral", SPOT + ["GET", "/api/v3/rebate/affiliate/referral", "--signed", "--params", '{"page":1,"pageSize":10}', "--execute"]),
    ("futures.market.ping", FUTURES + ["GET", "/api/v1/contract/ping", "--execute"]),
    ("futures.market.detail.all", FUTURES + ["GET", "/api/v1/contract/detail", "--execute"]),
    ("futures.market.detail.BTC_USDT", FUTURES + ["GET", "/api/v1/contract/detail", "--params", '{"symbol":"BTC_USDT"}', "--execute"]),
    ("futures.market.depth.BTC_USDT", FUTURES + ["GET", "/api/v1/contract/depth/BTC_USDT", "--params", '{"limit":20}', "--execute"]),
    ("futures.market.ticker.all", FUTURES + ["GET", "/api/v1/contract/ticker", "--execute"]),
    ("futures.market.ticker.BTC_USDT", FUTURES + ["GET", "/api/v1/contract/ticker", "--params", '{"symbol":"BTC_USDT"}', "--execute"]),
    ("futures.market.indexPrice.BTC_USDT", FUTURES + ["GET", "/api/v1/contract/index_price/BTC_USDT", "--execute"]),
    ("futures.market.fairPrice.BTC_USDT", FUTURES + ["GET", "/api/v1/contract/fair_price/BTC_USDT", "--execute"]),
    ("futures.market.fundingRate.BTC_USDT", FUTURES + ["GET", "/api/v1/contract/funding_rate/BTC_USDT", "--execute"]),
    ("futures.market.kline.BTC_USDT", FUTURES + ["GET", "/api/v1/contract/kline/BTC_USDT", "--params", '{"interval":"Min1"}', "--execute"]),
    ("futures.account.assets", FUTURES + ["GET", "/api/v1/private/account/assets", "--signed", "--execute"]),
    ("futures.account.asset.USDT", FUTURES + ["GET", "/api/v1/private/account/asset/USDT", "--signed", "--execute"]),
    ("futures.account.transferRecord.USDT", FUTURES + ["GET", "/api/v1/private/account/transfer_record", "--signed", "--params", '{"currency":"USDT"}', "--execute"]),
    ("futures.account.riskLimit.BTC_USDT", FUTURES + ["GET", "/api/v1/private/account/risk_limit", "--signed", "--params", '{"symbol":"BTC_USDT"}', "--execute"]),
    ("futures.account.tieredFee.BTC_USDT", FUTURES + ["GET", "/api/v1/private/account/tiered_fee_rate", "--signed", "--params", '{"symbol":"BTC_USDT"}', "--execute"]),
    ("futures.position.open.all", FUTURES + ["GET", "/api/v1/private/position/open_positions", "--signed", "--execute"]),
    ("futures.position.open.BTC_USDT", FUTURES + ["GET", "/api/v1/private/position/open_positions", "--signed", "--params", '{"symbol":"BTC_USDT"}', "--execute"]),
    ("futures.position.history.BTC_USDT", FUTURES + ["GET", "/api/v1/private/position/list/history_positions", "--signed", "--params", '{"symbol":"BTC_USDT","page_num":1,"page_size":20}', "--execute"]),
    ("futures.position.fundingRecords.BTC_USDT", FUTURES + ["GET", "/api/v1/private/position/funding_records", "--signed", "--params", '{"symbol":"BTC_USDT","page_num":1,"page_size":20}', "--execute"]),
    ("futures.position.leverage.BTC_USDT", FUTURES + ["GET", "/api/v1/private/position/leverage", "--signed", "--params", '{"symbol":"BTC_USDT"}', "--execute"]),
    ("futures.position.positionMode", FUTURES + ["GET", "/api/v1/private/position/position_mode", "--signed", "--execute"]),
    ("futures.orders.open.BTC_USDT", FUTURES + ["GET", "/api/v1/private/order/list/open_orders/BTC_USDT", "--signed", "--execute"]),
    ("futures.orders.history.BTC_USDT", FUTURES + ["GET", "/api/v1/private/order/list/history_orders", "--signed", "--params", '{"symbol":"BTC_USDT","page_num":1,"page_size":20}', "--execute"]),
    ("futures.orders.deals.BTC_USDT", FUTURES + ["GET", "/api/v1/private/order/list/order_deals", "--signed", "--params", '{"symbol":"BTC_USDT","page_num":1,"page_size":20}', "--execute"]),
    ("futures.plan.orders.BTC_USDT", FUTURES + ["GET", "/api/v1/private/planorder/list/orders", "--signed", "--params", '{"symbol":"BTC_USDT","states":"1"}', "--execute"]),
]

SKIPPED = [
    ("spot.orders.getOrder", "requires real symbol and orderId"),
    ("spot.subaccount.apiKey", "requires real subAccount"),
    ("spot.subaccount.asset", "requires real subAccount"),
    ("futures.orders.external", "requires real externalOid"),
    ("futures.orders.get", "requires real orderId"),
    ("futures.orders.batchQuery", "requires real orderIds"),
    ("futures.orders.dealDetails", "requires real orderId"),
    ("futures.stoporder.details", "requires real stop_order_id"),
]

SECRET_KEYS = {
    "listenkey",
    "address",
    "memo",
    "tag",
    "account",
    "fromaccount",
    "toaccount",
    "uid",
    "apikey",
    "secretkey",
    "refercode",
    "invitecode",
}


def redact(value: Any) -> Any:
    if isinstance(value, dict):
        output = {}
        for key, item in value.items():
            if key.lower() in SECRET_KEYS:
                output[key] = "<redacted>" if item not in (None, "", [], {}) else item
            else:
                output[key] = redact(item)
        return output
    if isinstance(value, list):
        return [redact(item) for item in value]
    return value


def summarize(value: Any) -> Any:
    if isinstance(value, list):
        return {"type": "list", "count": len(value), "sample": redact(value[:2])}
    if not isinstance(value, dict):
        return value

    return summarize_dict(redact(value), depth=0)


def summarize_dict(value: dict[str, Any], depth: int) -> dict[str, Any]:
    output: dict[str, Any] = {}
    for key, item in value.items():
        if isinstance(item, list):
            output[f"{key}_count"] = len(item)
            output[key] = summarize_list(item, depth + 1)
        elif isinstance(item, dict):
            output[key] = summarize_dict(item, depth + 1)
        else:
            output[key] = item
    return output


def summarize_list(value: list[Any], depth: int) -> Any:
    sample = value[:2] if depth >= 2 else value[:3]
    compacted = []
    for item in sample:
        if isinstance(item, dict):
            compacted.append(summarize_dict(item, depth + 1))
        elif isinstance(item, list):
            compacted.append(summarize_list(item, depth + 1))
        else:
            compacted.append(item)
    return {"type": "list", "count": len(value), "sample": compacted}


def parse_output(raw: str) -> Any:
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return raw[:1000]


def main() -> int:
    results = []
    for name, command in TESTS:
        proc = subprocess.run(
            command,
            cwd=ROOT,
            capture_output=True,
            timeout=30,
        )
        raw_bytes = (proc.stdout or b"") + (proc.stderr or b"")
        raw = raw_bytes.decode("utf-8", errors="replace").strip()
        results.append(
            {
                "name": name,
                "exit": proc.returncode,
                "output": summarize(parse_output(raw)),
            }
        )
        time.sleep(0.15)

    print(
        json.dumps(
            {
                "results": results,
                "skipped": [{"name": name, "reason": reason} for name, reason in SKIPPED],
            },
            indent=2,
            ensure_ascii=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
