# /// script
# requires-python = ">=3.12"
# dependencies = ["playwright>=1.52.0"]
# ///
"""Phase 0 browser automation smoke check."""

from __future__ import annotations

import json
import sys

from playwright.sync_api import sync_playwright


def main() -> int:
    report = {"browser": "chromium", "headless": True, "opened": "about:blank", "ok": False}
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(headless=True)
            page = browser.new_page()
            page.goto("about:blank")
            report["title"] = page.title()
            report["url"] = page.url
            browser.close()
            report["ok"] = True
    except Exception as exc:  # noqa: BLE001 - smoke script should report all failures.
        report["reason"] = str(exc)
        print(json.dumps(report, indent=2))
        return 1

    print(json.dumps(report, indent=2))
    return 0


if __name__ == "__main__":
    sys.exit(main())
