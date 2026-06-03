#!/usr/bin/env python3
"""Print one MEXC REST recipe section instead of opening the whole reference."""

from __future__ import annotations

import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
RECIPES = {
    "spot": ROOT / "skills" / "mexc-spot-rest" / "references" / "recipes.md",
    "futures": ROOT / "skills" / "mexc-futures-rest" / "references" / "recipes.md",
}
HELPERS = {
    "spot": "python skills/mexc-spot-rest/scripts/mexc_spot_request.py",
    "futures": "python skills/mexc-futures-rest/scripts/mexc_futures_request.py",
}
SECTION_ALIASES = {
    "spot": {
        "Market Data": "market public price ticker depth trade kline klines",
        "Account And Balances": "account balance balances asset kyc mytrades",
        "Spot Orders": "order orders cancel openorders test",
        "Listen Keys And Private Streams": "listen listenkey stream websocket userdatastream",
        "Wallet": "wallet deposit withdraw capital address network",
        "Sub-Accounts": "subaccount sub-account master transfer",
        "Rebates And Affiliate": "rebate affiliate refer commission tax",
    },
    "futures": {
        "Market Data": "market contract public price ticker depth kline funding",
        "Assets And Account": "account asset assets balance balances risk fee",
        "Positions": "position positions leverage margin funding",
        "Orders": "order orders cancel deal externaloid history",
        "Plan, TP/SL, And Trailing Orders": "plan tp sl stoploss takeprofit trailing stoporder planorder",
    },
}


def norm(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def sections(text: str) -> list[tuple[str, str]]:
    found: list[tuple[str, str]] = []
    title = ""
    body: list[str] = []
    for line in text.splitlines():
        if line.startswith("## "):
            if title:
                found.append((title, "\n".join(body).strip()))
            title = line[3:].strip()
            body = []
        elif title:
            body.append(line)
    if title:
        found.append((title, "\n".join(body).strip()))
    return found


def topic_matches(title: str, body: str, query: str) -> bool:
    return norm(query) in norm(f"{title}\n{body}")


def direct_section_matches(market: str, title: str, query: str) -> bool:
    aliases = SECTION_ALIASES.get(market, {}).get(title, "")
    choices = [title]
    choices.extend(aliases.split())
    return norm(query) in {norm(choice) for choice in choices}


def usage() -> int:
    markets = ", ".join(sorted(RECIPES))
    print(f"usage: recipe_lookup.py <{markets}> <topic-or-search>")
    return 2


def main() -> int:
    if len(sys.argv) < 3:
        return usage()

    market = sys.argv[1].lower()
    query = " ".join(sys.argv[2:])
    if market not in RECIPES:
        return usage()

    text = RECIPES[market].read_text(encoding="utf-8")
    parsed = sections(text)
    matches = [
        (title, body)
        for title, body in parsed
        if direct_section_matches(market, title, query)
    ]
    if not matches:
        matches = [(title, body) for title, body in parsed if topic_matches(title, body, query)]
    if not matches:
        print(f"No {market} recipe section matched: {query}")
        return 1

    print(f"helper: {HELPERS[market]}")
    for title, body in matches:
        print(f"\n## {title}")
        for line in body.splitlines():
            if line.strip() and not line.strip().startswith("```"):
                print(line)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
