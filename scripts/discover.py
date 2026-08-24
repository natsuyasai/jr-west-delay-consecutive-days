"""Diagnostic script (throwaway): fetch just the area/line master JSON."""
from __future__ import annotations

import json
import sys
import urllib.request

UA = "Mozilla/5.0 (compatible; jr-west-delay-consecutive-days/discovery)"
URL = "https://delay.trafficinfo.westjr.co.jp/api/fr/v1/ope/master/mst_area_line.json"


def main() -> int:
    req = urllib.request.Request(URL, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        body = resp.read().decode("utf-8", errors="replace")
    data = json.loads(body)
    print(json.dumps(data, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    sys.exit(main())
