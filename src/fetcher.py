"""
JR西日本の遅延情報取得モジュール

JR西日本の列車運行情報ページをスクレイピングして
遅延が発生している路線IDのセットを返す。
"""

from __future__ import annotations

import requests
from bs4 import BeautifulSoup

# JR西日本 列車運行情報ページ
TRAIN_INFO_URL = "https://www.jr-odekake.net/railroad/train_info/index.html"

# Webサイト上の路線名 → 内部ID のマッピング
LINE_NAME_TO_ID: dict[str, str] = {
    "山陽新幹線": "sanyo-shinkansen",
    "JR京都線": "kyoto-kobe",
    "JR神戸線": "kyoto-kobe",
    "大阪環状線": "osaka-loop",
    "学研都市線": "gakkentoshi",
    "おおさか東線": "osaka-higashi",
    "大和路線": "yamatoji",
    "阪和線": "hanwa",
    "きのくに線": "kinokuni",
    "湖西線": "kosei",
    "びわこ線": "biwako",
    "北陸線": "hokuriku",
    "山陰線": "sanin",
    "播但線": "bantan",
    "加古川線": "kakogawa",
    "姫新線": "hishin",
    "赤穂線": "ako",
    "境線": "sakaiminato",
    "伯備線": "hakubi",
    "芸備線": "geibi",
    "木次線": "kisuki",
    "山口線": "yamaguchi",
    "宇野みなと線": "uno-minato",
    "本四備讃線": "seto-ohashi",
    "瀬戸大橋線": "seto-ohashi",
    "津山線": "tsuyama",
    "吉備線": "kibi",
    "因美線": "inbi",
    "福塩線": "fukuen",
    "可部線": "kabe",
    "山陽線": "sanyo",
    "呉線": "kure",
    "岩徳線": "iwatoku",
    "小野田線": "onoda",
    "宇部線": "ube",
    "和歌山線": "wakayama",
    "桜井線": "sakurai",
    "草津線": "kusatsu",
    "関西線": "kansai",
    "福知山線": "fukuchiyama",
    "嵯峨野線": "sagano",
}


def fetch_delayed_lines() -> set[str]:
    """
    JR西日本Webサイトから遅延中の路線IDセットを取得する。

    Returns:
        遅延が発生している路線IDのセット (例: {"kyoto-kobe", "osaka-loop"})

    Raises:
        requests.RequestException: ネットワークエラー時
    """
    html = _fetch_html(TRAIN_INFO_URL)
    return _parse_delayed_lines(html)


def _fetch_html(url: str) -> str:
    """指定URLのHTMLを取得する。"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (compatible; JR-West-Delay-Counter/1.0)"
        )
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return response.text


def _parse_delayed_lines(html: str) -> set[str]:
    """
    HTMLをパースして遅延中の路線IDセットを返す。

    TODO: JR西日本サイトの実際のHTML構造に合わせて実装する。
          現在はスタブ実装。
    """
    soup = BeautifulSoup(html, "html.parser")
    delayed_ids: set[str] = set()

    # NOTE: 実際のHTML構造を確認してセレクタを調整する
    # 想定: 遅延中の路線名が特定のCSSクラスの要素に含まれている
    for element in soup.select(".train-info-delay, .delay-line"):
        line_name = element.get_text(strip=True)
        for key, line_id in LINE_NAME_TO_ID.items():
            if key in line_name:
                delayed_ids.add(line_id)

    return delayed_ids
