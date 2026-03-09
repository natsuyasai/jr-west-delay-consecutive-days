"""
YAML永続化モジュール

路線ごとの連続遅延日数の状態をYAMLファイルで保存・読み込みする。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path

import yaml

# JR西日本の全路線の初期定義
DEFAULT_LINES: list[dict] = [
    {"id": "sanyo-shinkansen", "name": "山陽新幹線"},
    {"id": "kyoto-kobe",       "name": "JR京都線・神戸線"},
    {"id": "osaka-loop",       "name": "大阪環状線"},
    {"id": "gakkentoshi",      "name": "学研都市線"},
    {"id": "osaka-higashi",    "name": "おおさか東線"},
    {"id": "yamatoji",         "name": "大和路線"},
    {"id": "hanwa",            "name": "阪和線"},
    {"id": "kinokuni",         "name": "きのくに線"},
    {"id": "kosei",            "name": "湖西線"},
    {"id": "biwako",           "name": "びわこ線"},
    {"id": "hokuriku",         "name": "北陸線"},
    {"id": "sanin",            "name": "山陰線"},
    {"id": "bantan",           "name": "播但線"},
    {"id": "kakogawa",         "name": "加古川線"},
    {"id": "hishin",           "name": "姫新線"},
    {"id": "ako",              "name": "赤穂線"},
    {"id": "sakaiminato",      "name": "境線"},
    {"id": "hakubi",           "name": "伯備線"},
    {"id": "geibi",            "name": "芸備線"},
    {"id": "kisuki",           "name": "木次線"},
    {"id": "yamaguchi",        "name": "山口線"},
    {"id": "uno-minato",       "name": "宇野みなと線"},
    {"id": "seto-ohashi",      "name": "本四備讃線(瀬戸大橋線)"},
    {"id": "tsuyama",          "name": "津山線"},
    {"id": "kibi",             "name": "吉備線"},
    {"id": "inbi",             "name": "因美線"},
    {"id": "fukuen",           "name": "福塩線"},
    {"id": "kabe",             "name": "可部線"},
    {"id": "sanyo",            "name": "山陽線"},
    {"id": "kure",             "name": "呉線"},
    {"id": "iwatoku",          "name": "岩徳線"},
    {"id": "onoda",            "name": "小野田線"},
    {"id": "ube",              "name": "宇部線"},
    {"id": "wakayama",         "name": "和歌山線"},
    {"id": "sakurai",          "name": "桜井線"},
    {"id": "kusatsu",          "name": "草津線"},
    {"id": "kansai",           "name": "関西線"},
    {"id": "fukuchiyama",      "name": "福知山線"},
    {"id": "sagano",           "name": "嵯峨野線"},
]


@dataclass
class LineState:
    id: str
    name: str
    consecutive_days: int = 0
    start_date: date | None = None


@dataclass
class AppState:
    last_updated: date | None = None
    lines: list[LineState] = field(default_factory=list)


def load_state(path: Path) -> AppState:
    """
    YAMLファイルから状態を読み込む。

    ファイルが存在しない場合は全路線を初期値(0日)で生成して返す。
    """
    if not path.exists():
        return _default_state()

    with path.open(encoding="utf-8") as f:
        data = yaml.safe_load(f)

    if not data:
        return _default_state()

    lines = [
        LineState(
            id=line["id"],
            name=line["name"],
            consecutive_days=line.get("consecutive_days", 0),
            start_date=line.get("start_date"),  # date or None
        )
        for line in data.get("lines", [])
    ]

    last_updated = data.get("last_updated")  # date or None

    return AppState(last_updated=last_updated, lines=lines)


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
            }
            for line in state.lines
        ],
    }

    with path.open("w", encoding="utf-8") as f:
        yaml.dump(data, f, allow_unicode=True, default_flow_style=False)


def _default_state() -> AppState:
    """全路線を連続日数0で初期化した状態を返す。"""
    lines = [
        LineState(id=d["id"], name=d["name"])
        for d in DEFAULT_LINES
    ]
    return AppState(last_updated=None, lines=lines)
