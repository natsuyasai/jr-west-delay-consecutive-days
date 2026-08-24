"""Diagnostic script (throwaway): fetch the actual JSON API endpoints found
by reverse-engineering the delay-certificate SPA's app.js bundle, and dump
their real response shape.
"""
from __future__ import annotations

import json
import sys
import urllib.request

UA = "Mozilla/5.0 (compatible; jr-west-delay-consecutive-days/discovery)"
BASE = "https://delay.trafficinfo.westjr.co.jp/api/fr/v1"

ENDPOINTS = [
    f"{BASE}/ope/master/mst_area_line.json",
    f"{BASE}/ope/master/mst_time_zone.json",
    f"{BASE}/history/ope/delay_certificate/4.json",
    f"{BASE}/history/ope/delay_certificate/12.json",
]


def fetch(url: str) -> None:
    print("=" * 100)
    print("URL:", url)
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            status = resp.status
            body = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR: {exc!r}")
        return
    print(f"status={status} length={len(body)}")
    try:
        data = json.loads(body)
    except Exception as exc:  # noqa: BLE001
        print(f"NOT JSON ({exc!r}), raw head:")
        print(body[:2000])
        return
    pretty = json.dumps(data, ensure_ascii=False, indent=2)
    print(pretty[:6000])
    print("... [truncated]" if len(pretty) > 6000 else "")


def main() -> int:
    for url in ENDPOINTS:
        fetch(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
