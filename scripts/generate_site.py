"""Build docs/data.json, the data file the static site (docs/index.html)
fetches at runtime, from data/lines.json and data/history/*.json.

Run after scripts/fetch_delay.py. docs/index.html itself is a static,
hand-maintained file and is not touched by this script.
"""
from __future__ import annotations

import json
import sys
from datetime import datetime
from pathlib import Path
from zoneinfo import ZoneInfo

JST = ZoneInfo("Asia/Tokyo")
ROOT = Path(__file__).resolve().parent.parent
DATA_DIR = ROOT / "data"
HISTORY_DIR = DATA_DIR / "history"
LINES_PATH = DATA_DIR / "lines.json"
STATE_PATH = DATA_DIR / "state.json"
DOCS_DIR = ROOT / "docs"
OUTPUT_PATH = DOCS_DIR / "data.json"


def main() -> int:
    if not LINES_PATH.exists():
        print("data/lines.json not found; run scripts/fetch_delay.py first.")
        return 1

    lines = json.loads(LINES_PATH.read_text(encoding="utf-8"))

    areas: dict[int, str] = {}
    for line in lines:
        areas.setdefault(line["area_id"], line["area_name"])
    area_list = [{"area_id": aid, "display_name": name} for aid, name in sorted(areas.items())]

    delays: dict[str, dict] = {}
    dates: list[str] = []
    for path in sorted(HISTORY_DIR.glob("*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        delays[d["date"]] = d["lines"]
        dates.append(d["date"])
    dates.sort()

    streak_start_truncated = {}
    if STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text(encoding="utf-8"))
        streak_start_truncated = state.get("streak_start_truncated", {})

    DOCS_DIR.mkdir(parents=True, exist_ok=True)
    payload = {
        "generated_at": datetime.now(JST).isoformat(),
        "areas": area_list,
        "lines": lines,
        "dates": dates,
        "latest_date": dates[-1] if dates else None,
        "delays": delays,
        # per line_id: true if the current streak's start date is the
        # earliest date archived for that line, i.e. the streak may have
        # actually begun even earlier than what we can show.
        "streak_start_truncated": streak_start_truncated,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False) + "\n", encoding="utf-8")
    print(f"Wrote {OUTPUT_PATH} with {len(dates)} dates, {len(lines)} lines.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
