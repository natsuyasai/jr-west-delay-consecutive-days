"""Diagnostic script (throwaway): the delay-certificate site is a JS SPA that
serves the same static shell for every route, so plain HTML fetches are
useless. This instead pulls the app's JS bundle and greps it for API-looking
URL fragments so the real data endpoints can be found.

Meant to run once via GitHub Actions (this sandbox's egress to
delay.trafficinfo.westjr.co.jp is blocked; GH-hosted runners have normal
internet access).
"""
from __future__ import annotations

import re
import sys
import urllib.request

UA = "Mozilla/5.0 (compatible; jr-west-delay-consecutive-days/discovery)"
BASE = "https://delay.trafficinfo.westjr.co.jp"

BUNDLE_URLS = [
    f"{BASE}/static/js/manifest.ce07dc6eab3dff1f54e1.js",
    f"{BASE}/static/js/vendor.6c20359410e9c12023fc.js",
    f"{BASE}/static/js/app.805b2d220e7e9e9132ed.js",
]

URL_LIKE_RE = re.compile(r"""["'`](/(?:api|v\d)[^"'`]{0,120}|https?://[a-zA-Z0-9.\-]*westjr[^"'`]{0,120})["'`]""")
API_WORD_RE = re.compile(r".{40}(?:api|endpoint|baseURL|axios\.create)[^\n]{0,80}", re.IGNORECASE)


def fetch(url: str) -> str | None:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return resp.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR fetching {url}: {exc!r}")
        return None


def main() -> int:
    for url in BUNDLE_URLS:
        print("=" * 100)
        print("BUNDLE:", url)
        print("=" * 100)
        body = fetch(url)
        if body is None:
            continue
        print(f"length={len(body)}")

        url_matches = sorted(set(m.group(1) for m in URL_LIKE_RE.finditer(body)))
        print(f"-- {len(url_matches)} url-like matches --")
        for m in url_matches[:200]:
            print(" ", m)

        api_word_matches = sorted(set(m.group(0) for m in API_WORD_RE.finditer(body)))
        print(f"-- {len(api_word_matches)} 'api' keyword context matches --")
        for m in api_word_matches[:200]:
            print(" ", m)
        print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
