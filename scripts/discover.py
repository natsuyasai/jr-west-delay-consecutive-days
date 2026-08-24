"""Diagnostic script (throwaway): dump raw HTML of JR West delay-certificate
pages so the real page structure can be inspected via GitHub Actions job
logs. The sandbox this was authored in cannot reach delay.trafficinfo.westjr.co.jp
(egress-blocked), so this script is meant to be run once via workflow_dispatch
on a GitHub-hosted runner, which has normal internet access.
"""
from __future__ import annotations

import sys
import urllib.request

UA = "Mozilla/5.0 (compatible; jr-west-delay-consecutive-days/discovery)"

URLS = [
    "https://delay.trafficinfo.westjr.co.jp/",
    "https://delay.trafficinfo.westjr.co.jp/sp/1",
    "https://delay.trafficinfo.westjr.co.jp/sp/2",
    "https://delay.trafficinfo.westjr.co.jp/sp/3",
    "https://delay.trafficinfo.westjr.co.jp/sp/4",
    "https://delay.trafficinfo.westjr.co.jp/sp/5",
    "https://delay.trafficinfo.westjr.co.jp/sp/6",
    "https://delay.trafficinfo.westjr.co.jp/sp/history/2/4",
    "https://delay.trafficinfo.westjr.co.jp/sp/delay-certificate/history/2/12/2026-06-13/5",
]


def fetch(url: str) -> None:
    print("=" * 100)
    print("URL:", url)
    print("=" * 100)
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    try:
        with urllib.request.urlopen(req, timeout=20) as resp:
            status = resp.status
            final_url = resp.geturl()
            body = resp.read().decode("utf-8", errors="replace")
    except Exception as exc:  # noqa: BLE001
        print(f"ERROR fetching {url}: {exc!r}")
        return
    print(f"status={status} final_url={final_url} length={len(body)}")
    print(body)
    print()


def main() -> int:
    for url in URLS:
        fetch(url)
    return 0


if __name__ == "__main__":
    sys.exit(main())
