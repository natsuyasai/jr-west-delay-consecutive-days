"""
YAML永続化モジュール

路線ごとの連続遅延日数の状態をYAMLファイルで保存・読み込みする。

路線IDはJR西日本の非公式API (train-guide.westjr.co.jp) の
trafficinfo レスポンスで使われるIDと一致させる。
初回実行時に area_master API から路線リストを動的取得する。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date
from pathlib import Path
from typing import TYPE_CHECKING

import yaml

if TYPE_CHECKING:
    pass

# 初回実行時のフォールバック用デフォルト路線リスト
# (API取得失敗時 or オフライン時に使用)
# IDは train-guide.westjr.co.jp/api/v3/ の trafficinfo キーと一致
FALLBACK_LINES: list[dict[str, str]] = [
    # 近畿エリア
    {"id": "hokurikubiwako", "name": "北陸線・琵琶湖線"},
    {"id": "kobesanyo",      "name": "JR神戸線・山陽線"},
    {"id": "kyoto",          "name": "JR京都線"},
    {"id": "ako",            "name": "赤穂線"},
    {"id": "kosei",          "name": "湖西線"},
    {"id": "nara",           "name": "奈良線"},
    {"id": "sagano",         "name": "嵯峨野線"},
    {"id": "sanin1",         "name": "山陰線（近畿）"},
    {"id": "osakahigashi",   "name": "おおさか東線"},
    {"id": "takarazuka",     "name": "JR宝塚線"},
    {"id": "gakkentoshi",    "name": "学研都市線・JR東西線"},
    {"id": "osakaloop",      "name": "大阪環状線・JRゆめ咲線"},
    {"id": "yamatoji",       "name": "大和路線"},
    {"id": "hanwa",          "name": "阪和線・関西空港線"},
    {"id": "kusatsu",        "name": "草津線"},
    {"id": "fukuchiyama",    "name": "JR宝塚線・福知山線"},
    # 中国エリア
    {"id": "sanin2",         "name": "山陰線（中国）"},
    {"id": "bantan",         "name": "播但線"},
    {"id": "hishin",         "name": "姫新線"},
    {"id": "ako",            "name": "赤穂線"},
    {"id": "hakubi",         "name": "伯備線"},
    {"id": "geibi",          "name": "芸備線"},
    {"id": "kisuki",         "name": "木次線"},
    {"id": "yamaguchi",      "name": "山口線"},
    {"id": "unominato",      "name": "宇野みなと線"},
    {"id": "setoohashi",     "name": "本四備讃線(瀬戸大橋線)"},
    {"id": "tsuyama",        "name": "津山線"},
    {"id": "kibi",           "name": "吉備線"},
    {"id": "inbi",           "name": "因美線"},
    {"id": "fukuen",         "name": "福塩線"},
    {"id": "kabe",           "name": "可部線"},
    {"id": "kure",           "name": "呉線"},
    {"id": "iwatoku",        "name": "岩徳線"},
    {"id": "onoda",          "name": "小野田線"},
    {"id": "ube",            "name": "宇部線"},
    {"id": "sakai",          "name": "境線"},
    {"id": "kakogawa",       "name": "加古川線"},
    # 北陸エリア
    {"id": "hokuriku",       "name": "北陸線"},
    # 新幹線
    {"id": "sanyoshinkansen", "name": "山陽新幹線"},
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
    このとき fetcher.fetch_all_line_ids() の呼び出しは main.py 側で行い、
    引数 initial_lines として渡す。
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


def build_initial_state(line_defs: list[dict[str, str]]) -> AppState:
    """
    路線定義リストから初期状態を生成する。

    Args:
        line_defs: [{"id": "kobesanyo", "name": "JR神戸線・山陽線"}, ...]
                   fetch_all_line_ids() または FALLBACK_LINES を渡す。
    """
    seen: set[str] = set()
    lines = []
    for d in line_defs:
        if d["id"] not in seen:
            lines.append(LineState(id=d["id"], name=d["name"]))
            seen.add(d["id"])
    return AppState(last_updated=None, lines=lines)


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
    """フォールバック路線リストで初期状態を生成する。"""
    return build_initial_state(FALLBACK_LINES)
