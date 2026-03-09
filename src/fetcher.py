"""
JR西日本の遅延情報取得モジュール

JR西日本の非公式JSON APIを使って遅延（運行障害）が発生している
路線IDのセットを返す。

APIベースURL: https://www.train-guide.westjr.co.jp/api/v3/
参考: https://qiita.com/k_kado__j_ichi/items/7081bc62618bef32eb0e
"""

from __future__ import annotations

import logging

import requests

logger = logging.getLogger(__name__)

BASE_URL = "https://www.train-guide.westjr.co.jp/api/v3"

# 取得対象エリア
# area_{AREA}_trafficinfo.json / area_{AREA}_master.json に対応
AREAS = ["kinki", "chugoku", "hokuriku", "shinkansen"]


def fetch_delayed_lines() -> set[str]:
    """
    各エリアの trafficinfo API から遅延・運行障害が発生している
    路線IDのセットを取得する。

    JR西日本は運行に支障が生じた路線を trafficinfo の `lines` キーに格納する。
    `lines` が空の場合は全路線平常運転。

    Returns:
        遅延が発生している路線IDのセット (例: {"kobesanyo", "bantan"})

    Raises:
        requests.RequestException: ネットワークエラー時
    """
    delayed: set[str] = set()

    for area in AREAS:
        try:
            area_delayed = _fetch_area_trafficinfo(area)
            delayed |= area_delayed
            logger.debug("area=%s delayed_lines=%s", area, area_delayed)
        except requests.HTTPError as e:
            # エリアによってはエンドポイントが存在しない場合があるためスキップ
            logger.warning("area=%s trafficinfo取得失敗: %s", area, e)

    return delayed


def fetch_all_line_ids() -> list[dict[str, str]]:
    """
    各エリアの master API から全路線情報（id・name）のリストを取得する。
    state.yaml の初回初期化時に使用する。

    Returns:
        [{"id": "kobesanyo", "name": "JR神戸線・山陽線"}, ...]

    Raises:
        requests.RequestException: ネットワークエラー時
    """
    lines: list[dict[str, str]] = []
    seen_ids: set[str] = set()

    for area in AREAS:
        try:
            area_lines = _fetch_area_master(area)
            for line in area_lines:
                if line["id"] not in seen_ids:
                    lines.append(line)
                    seen_ids.add(line["id"])
        except requests.HTTPError as e:
            logger.warning("area=%s master取得失敗: %s", area, e)

    return lines


# ---------------------------------------------------------------------------
# 内部実装
# ---------------------------------------------------------------------------

def _fetch_area_trafficinfo(area: str) -> set[str]:
    """
    指定エリアの trafficinfo JSON から遅延路線IDセットを返す。

    レスポンス例 (平常時): {"lines": {}, "express": {}}
    レスポンス例 (障害時): {"lines": {"bantan": {"info": "遅延", ...}}, "express": {}}

    `lines` の各キーが遅延発生路線のID。
    """
    url = f"{BASE_URL}/area_{area}_trafficinfo.json"
    data = _get_json(url)
    return set(data.get("lines", {}).keys())


def _fetch_area_master(area: str) -> list[dict[str, str]]:
    """
    指定エリアの master JSON から路線情報リストを返す。

    レスポンス例:
    {
        "line": [
            {"id": "kobesanyo", "name": "JR神戸線・山陽線", ...},
            ...
        ]
    }
    """
    url = f"{BASE_URL}/area_{area}_master.json"
    data = _get_json(url)

    lines = []
    for entry in data.get("line", []):
        if "id" in entry and "name" in entry:
            lines.append({"id": entry["id"], "name": entry["name"]})
    return lines


def _get_json(url: str) -> dict:
    """GET リクエストを送ってJSONをデコードして返す。"""
    response = requests.get(url, timeout=30)
    response.raise_for_status()
    return response.json()
