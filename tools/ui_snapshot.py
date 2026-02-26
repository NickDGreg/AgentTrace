"""Capture deterministic UI snapshots for AgentTrace sites."""

from __future__ import annotations

import argparse
import json
import os
from pathlib import Path
from typing import Sequence


def main(argv: Sequence[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Capture a screenshot using Playwright. "
            "Useful for agent-visible UI checks in CI and local harness runs."
        )
    )
    parser.add_argument(
        "--url",
        default=os.environ.get("AGENTTRACE_START_URL"),
        help="Page URL to open. Defaults to AGENTTRACE_START_URL.",
    )
    parser.add_argument(
        "--out",
        default="results/ui/latest.png",
        help="Output screenshot path.",
    )
    parser.add_argument(
        "--wait-for-selector",
        help="Optional CSS selector to wait for before taking screenshot.",
    )
    parser.add_argument(
        "--click",
        action="append",
        default=[],
        help="CSS selector to click before screenshot (repeatable).",
    )
    parser.add_argument(
        "--timeout-ms",
        type=int,
        default=15000,
        help="Timeout in milliseconds for navigation and actions.",
    )
    parser.add_argument(
        "--viewport-width",
        type=int,
        default=1366,
        help="Browser viewport width.",
    )
    parser.add_argument(
        "--viewport-height",
        type=int,
        default=900,
        help="Browser viewport height.",
    )
    parser.add_argument(
        "--full-page",
        action="store_true",
        help="Capture the full page instead of viewport only.",
    )
    args = parser.parse_args(argv)

    if not args.url:
        print(
            json.dumps(
                {"error": {"message": "missing --url or AGENTTRACE_START_URL"}}
            )
        )
        return 1

    try:
        capture_snapshot(
            url=args.url,
            output=Path(args.out),
            wait_for_selector=args.wait_for_selector,
            click_selectors=list(args.click),
            timeout_ms=args.timeout_ms,
            viewport_width=args.viewport_width,
            viewport_height=args.viewport_height,
            full_page=args.full_page,
        )
    except RuntimeError as exc:
        print(json.dumps({"error": {"message": str(exc)}}))
        return 2

    print(
        json.dumps(
            {
                "ok": True,
                "url": args.url,
                "screenshot": str(Path(args.out).resolve()),
            }
        )
    )
    return 0


def capture_snapshot(
    *,
    url: str,
    output: Path,
    wait_for_selector: str | None,
    click_selectors: list[str],
    timeout_ms: int,
    viewport_width: int,
    viewport_height: int,
    full_page: bool,
) -> None:
    try:
        from playwright.sync_api import sync_playwright
    except ImportError as exc:
        raise RuntimeError(
            "playwright is not installed. Install dev dependencies and run "
            "`playwright install chromium` before using ui_snapshot."
        ) from exc

    output.parent.mkdir(parents=True, exist_ok=True)

    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(headless=True)
        page = browser.new_page(
            viewport={"width": viewport_width, "height": viewport_height}
        )
        page.goto(url, wait_until="domcontentloaded", timeout=timeout_ms)
        for selector in click_selectors:
            page.click(selector, timeout=timeout_ms)
        if wait_for_selector:
            page.wait_for_selector(wait_for_selector, timeout=timeout_ms)
        page.screenshot(path=str(output), full_page=full_page)
        browser.close()


if __name__ == "__main__":
    raise SystemExit(main())

