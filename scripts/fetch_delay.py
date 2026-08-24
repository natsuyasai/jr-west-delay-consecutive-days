"""Fetch JR West delay-certificate data and update the local history archive.

Meant to run once a day, before the first trains depart (see
.github/workflows/daily.yml). For every JR West line it reads whether a
delay certificate was issued on each finalized (i.e. not today) date and
recomputes the consecutive-day ("connected") delay streak.

Data source: the unofficial-but-public JSON API behind
https://delay.trafficinfo.westjr.co.jp/ (JR West's own delay-certificate
site). There is no documented/official API, so this talks to the same
endpoints the site's own frontend uses:

  GET /api/fr/v1/ope/master/mst_area_line.json
      -> area & line master data (names, ids)
  GET /api/fr/v1/history/ope/delay_certificate/{line_id}.json
      -> per-line delay-certificate history (roughly the last 45 days),
         each entry: {date, have_delay_certificate, data: [...]}
"""
from __future__ import annotations

import json
import sys
import urllib.error
import urllib.request
from datetime import date, datetime
from pathlib import Path
from zoneinfo import ZoneInfo

UA = (
    "Mozilla/5.0 (compatible; jr-west-delay-consecutive-days/1.0; "
    "+https://github.com/natsuyasai/jr-west-delay-consecutive-days)"
)
API_BASE = "https://delay.trafficinfo.westjr.co.jp/api/fr/v1"
JST = ZoneInfo("Asia/Tokyo")

ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
HISTORY_DIR = DATA_DIR / "history"
LINES_PATH = DATA_DIR / "lines.json"
STATE_PATH = DATA_DIR / "state.json"


def fetch_json(url: str) -> dict:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return json.loads(resp.read().decode("utf-8"))


def fetch_lines() -> list[dict]:
    data = fetch_json(f"{API_BASE}/ope/master/mst_area_line.json")
    lines = []
    for area in data["areas"]:
        for line in area["lines"]:
            lines.append(
                {
                    "line_id": line["line_id"],
                    "area_id": area["area_id"],
                    "area_name": area["display_name"],
                    "line_name": line["line_name"],
                    "section_name": line.get("section_name", ""),
                }
            )
    lines.sort(key=lambda l: (l["area_id"], l["line_id"]))
    return lines


def fetch_line_history(line_id: int) -> dict[str, bool]:
    """Return {date_str: have_delay_certificate} for one line."""
    url = f"{API_BASE}/history/ope/delay_certificate/{line_id}.json"
    data = fetch_json(url)
    result = {}
    for entry in data.get("delay_certificates", []):
        result[entry["date"]] = bool(entry["have_delay_certificate"])
    return result


def load_existing_history() -> dict[str, dict[str, bool]]:
    """{date_str: {line_id_str: delayed}} for dates already on disk."""
    out: dict[str, dict[str, bool]] = {}
    if not HISTORY_DIR.exists():
        return out
    for path in HISTORY_DIR.glob("*.json"):
        d = json.loads(path.read_text(encoding="utf-8"))
        out[d["date"]] = {lid: info["delayed"] for lid, info in d["lines"].items()}
    return out


def main() -> int:
    HISTORY_DIR.mkdir(parents=True, exist_ok=True)

    today_jst = datetime.now(JST).date()

    print("Fetching area/line master...")
    lines = fetch_lines()
    LINES_PATH.write_text(
        json.dumps(lines, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    print(f"  {len(lines)} lines across {len({l['area_id'] for l in lines})} areas")

    merged = load_existing_history()

    fetch_errors = 0
    for line in lines:
        line_id = str(line["line_id"])
        try:
            hist = fetch_line_history(line["line_id"])
        except (urllib.error.URLError, TimeoutError) as exc:
            print(f"  ERROR fetching line {line_id} ({line['line_name']}): {exc!r} -- skipping")
            fetch_errors += 1
            continue
        for date_str, delayed in hist.items():
            if date.fromisoformat(date_str) >= today_jst:
                continue  # not finalized yet, skip
            merged.setdefault(date_str, {})[line_id] = delayed

    all_dates = sorted(merged.keys())
    if not all_dates:
        print("No history data available; aborting.")
        return 1

    line_ids = [str(l["line_id"]) for l in lines]
    streak = {lid: 0 for lid in line_ids}
    prev_date: date | None = None
    per_date_output: dict[str, dict[str, dict]] = {}

    for date_str in all_dates:
        d = date.fromisoformat(date_str)
        day_map = merged[date_str]
        contiguous = prev_date is not None and (d - prev_date).days == 1
        per_date_output[date_str] = {}
        for lid in line_ids:
            delayed = day_map.get(lid)
            if delayed is None:
                continue
            if not contiguous:
                streak[lid] = 0
            streak[lid] = streak[lid] + 1 if delayed else 0
            per_date_output[date_str][lid] = {"delayed": delayed, "streak": streak[lid]}
        prev_date = d

    written = 0
    for date_str, line_map in per_date_output.items():
        if not line_map:
            continue
        out_path = HISTORY_DIR / f"{date_str}.json"
        out_path.write_text(
            json.dumps({"date": date_str, "lines": line_map}, ensure_ascii=False, indent=2)
            + "\n",
            encoding="utf-8",
        )
        written += 1

    latest_date = all_dates[-1]
    state = {
        "latest_date": latest_date,
        "updated_at": datetime.now(JST).isoformat(),
        "streaks": {
            lid: per_date_output[latest_date].get(lid, {}).get("streak", 0) for lid in line_ids
        },
    }
    STATE_PATH.write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )

    print(
        f"Done. Latest finalized date: {latest_date}. "
        f"{written}/{len(all_dates)} date files written. "
        f"{fetch_errors} line(s) failed to fetch this run."
    )
    return 1 if fetch_errors == len(lines) else 0


if __name__ == "__main__":
    sys.exit(main())
