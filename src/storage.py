"""
YAML永続化モジュール

路線ごとの連続遅延日数の状態をYAMLファイルで保存・読み込みする。
対象は近畿エリアの路線のみ。

路線IDは fetcher.py の ROUTE_NAME_TO_ID と一致させること。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

# 近畿エリアの路線定義
# id: fetcher.ROUTE_NAME_TO_ID の値と一致
# name: X投稿など表示に使う路線名
KINKI_LINES: list[dict[str, str]] = [
    {"id": "hokurikubiwako", "name": "北陸線・琵琶湖線"},
    {"id": "kyoto",          "name": "JR京都線"},
    {"id": "kobesanyo",      "name": "JR神戸線・山陽線"},
    {"id": "ako",            "name": "赤穂線"},
    {"id": "kosei",          "name": "湖西線"},
    {"id": "kusatsu",        "name": "草津線"},
    {"id": "nara",           "name": "奈良線"},
    {"id": "sagano",         "name": "嵯峨野線"},
    {"id": "osakahigashi",   "name": "おおさか東線"},
    {"id": "takarazuka",     "name": "JR宝塚線"},
    {"id": "tozai",          "name": "JR東西線"},
    {"id": "gakkentoshi",    "name": "学研都市線"},
    {"id": "osakaloop",      "name": "大阪環状線"},
    {"id": "yumesaki",       "name": "JRゆめ咲線"},
    {"id": "yamatoji",       "name": "大和路線"},
    {"id": "hanwa",          "name": "阪和線・羽衣線"},
    {"id": "kansaikuko",     "name": "関西空港線"},
    {"id": "wakayama",       "name": "和歌山線"},
    {"id": "manyomahora",    "name": "万葉まほろば線"},
    {"id": "kansai",         "name": "関西線"},
    {"id": "wadamisaki",     "name": "和田岬線"},
    {"id": "kakogawa",       "name": "加古川線"},
    {"id": "hishin",         "name": "姫新線"},
]


@dataclass
class LineState:
    id: str
    name: str
    consecutive_days: int = 0
    start_date: date | None = None
    no_delay_consecutive_days: int = 0
    no_delay_start_date: date | None = None


@dataclass
class AppState:
    last_updated: date | None = None
    lines: list[LineState] = field(default_factory=list)


def load_state(path: Path) -> AppState:
    """
    YAMLファイルから状態を読み込む。
    ファイルが存在しない場合は KINKI_LINES で初期状態を生成する。
    """
    if not path.exists():
        return build_initial_state()

    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        return build_initial_state()

    lines = [
        LineState(
            id=line["id"],
            name=line["name"],
            consecutive_days=line.get("consecutive_days", 0),
            start_date=line.get("start_date"),
            no_delay_consecutive_days=line.get("no_delay_consecutive_days", 0),
            no_delay_start_date=line.get("no_delay_start_date"),
        )
        for line in data.get("lines", [])
    ]
    return AppState(last_updated=data.get("last_updated"), lines=lines)


def save_state(path: Path, state: AppState) -> None:
    """状態をYAMLファイルに書き込む。"""
    path.parent.mkdir(parents=True, exist_ok=True)

    data = {
        "last_updated": state.last_updated,
        "lines": [
            {
                "id": line.id,
                "name": line.name,
                "consecutive_days": line.consecutive_days,
                "start_date": line.start_date,
                "no_delay_consecutive_days": line.no_delay_consecutive_days,
                "no_delay_start_date": line.no_delay_start_date,
            }
            for line in state.lines
        ],
    }

    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


def build_initial_state() -> AppState:
    """KINKI_LINES をもとに全路線0日の初期状態を返す。"""
    lines = [LineState(id=d["id"], name=d["name"]) for d in KINKI_LINES]
    return AppState(last_updated=None, lines=lines)
