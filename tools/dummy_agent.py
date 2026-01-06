"""Dummy agent for smoke-testing AgentTrace."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import urllib.error
import urllib.request
from typing import Mapping

BTC_PATTERN = re.compile(r"(bc1[0-9a-z]{25,62})", re.IGNORECASE)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Dummy agent that fetches a page and extracts a BTC address.")
    parser.add_argument("--url", default=os.environ.get("AGENTTRACE_START_URL"), help="URL to fetch.")
    args = parser.parse_args(argv)

    if not args.url:
        print(json.dumps({"error": {"message": "No URL provided via --url or AGENTTRACE_START_URL"}}))
        return 1

    output = generate_agent_output(args.url)
    print(json.dumps(output))
    return 0


def generate_agent_output(url: str) -> Mapping[str, object]:
    try:
        html = _fetch(url)
    except urllib.error.URLError as exc:
        return {"error": {"message": f"Failed to fetch {url}: {exc.reason}"}}

    address = extract_btc_address(html)
    if not address:
        return {"error": {"message": "BTC address not found in page"}}

    return {"artifacts": {"BTC": address}}


def extract_btc_address(html: str) -> str | None:
    match = BTC_PATTERN.search(html)
    return match.group(1) if match else None


def _fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": "AgentTraceDummy/0.1"})
    with urllib.request.urlopen(req, timeout=10) as response:
        return response.read().decode("utf-8", errors="replace")


if __name__ == "__main__":
    sys.exit(main())
