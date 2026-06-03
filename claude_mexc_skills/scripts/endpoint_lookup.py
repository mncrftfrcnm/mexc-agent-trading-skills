#!/usr/bin/env python3
"""Print a narrow MEXC REST endpoint catalog slice."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parent
CATALOG = ROOT / "mexc_endpoints.json"


def norm(value: str) -> str:
    return "".join(ch for ch in value.lower() if ch.isalnum())


def load_catalog() -> dict[str, Any]:
    return json.loads(CATALOG.read_text(encoding="utf-8"))


def usage(catalog: dict[str, Any]) -> int:
    markets = ", ".join(sorted(catalog))
    print(f"usage: endpoint_lookup.py <{markets}> <topic-or-search>")
    for market, data in catalog.items():
        topics = ", ".join(data["topics"])
        print(f"{market}: {topics}")
    return 2


def topic_matches(key: str, topic: dict[str, Any], query: str) -> bool:
    q = norm(query)
    haystack = [key, topic.get("auth", "")]
    haystack.extend(topic.get("aliases", []))
    haystack.extend(topic.get("endpoints", []))
    haystack.extend(topic.get("notes", []))
    return q in norm(" ".join(haystack))


def direct_topic_matches(key: str, topic: dict[str, Any], query: str) -> bool:
    q = norm(query)
    choices = [key]
    choices.extend(topic.get("aliases", []))
    return q in {norm(choice) for choice in choices}


def main() -> int:
    catalog = load_catalog()
    if len(sys.argv) < 3:
        return usage(catalog)

    market = sys.argv[1].lower()
    query = " ".join(sys.argv[2:])
    if market not in catalog:
        return usage(catalog)

    data = catalog[market]
    matches = [
        (key, topic)
        for key, topic in data["topics"].items()
        if direct_topic_matches(key, topic, query)
    ]
    if not matches:
        matches = [
            (key, topic)
            for key, topic in data["topics"].items()
            if topic_matches(key, topic, query)
        ]
    if not matches:
        print(f"No {market} endpoint topic matched: {query}")
        return 1

    print(f"{data['name']}")
    print(f"base_url: {data['base_url']}")
    for key, topic in matches:
        print(f"\n[{key}] auth: {topic['auth']}")
        for endpoint in topic.get("endpoints", []):
            print(f"- {endpoint}")
        for note in topic.get("notes", []):
            print(f"note: {note}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
