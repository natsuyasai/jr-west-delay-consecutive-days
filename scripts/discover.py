"""Diagnostic script (throwaway): dump wide context around the API base URL
and route-looking keywords found in the delay-certificate SPA's app.js
bundle, so the real REST endpoints can be reconstructed.
"""
from __future__ import annotations

import re
import sys
import urllib.request

UA = "Mozilla/5.0 (compatible; jr-west-delay-consecutive-days/discovery)"
APP_JS = "https://delay.trafficinfo.westjr.co.jp/static/js/app.805b2d220e7e9e9132ed.js"

KEYWORDS = [
    "api/fr/v1",
    "areas",
    "/lines",
    "lineId",
    "delay-certificate",
    "delayCertificate",
    "certificates",
    "/history",
    "historys",
    "master",
    "targetDate",
    ".get(\"",
    ".get('",
    "Qt=",
    "Ot=",
]


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def main() -> int:
    body = fetch(APP_JS)
    print(f"app.js length={len(body)}")

    for kw in KEYWORDS:
        idxs = [m.start() for m in re.finditer(re.escape(kw), body)]
        print("=" * 100)
        print(f"keyword={kw!r} occurrences={len(idxs)}")
        for idx in idxs[:6]:
            start = max(0, idx - 150)
            end = min(len(body), idx + 350)
            print("-" * 80)
            print(body[start:end])
    return 0


if __name__ == "__main__":
    sys.exit(main())
