"""
JR西日本 近畿エリア 運行情報履歴取得モジュール

近畿エリアの運行情報履歴ページをスクレイピングして
指定日に遅延が発生した路線IDのセットを返す。

データソース:
  https://trafficinfo.westjr.co.jp/kinki_history.html
  過去7日分の運行情報履歴が掲載されている。
"""

from __future__ import annotations

import logging
import re
import unicodedata
from datetime import date

import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

HISTORY_URL = "https://trafficinfo.westjr.co.jp/kinki_history.html"

# 履歴ページの【】内テキスト → 内部ID マッピング
# 同一路線が複数表記される場合はすべてのバリエーションを登録する
ROUTE_NAME_TO_ID: dict[str, str] = {
    "北陸線":       "hokurikubiwako",
    "琵琶湖線":     "hokurikubiwako",
    "びわこ線":     "hokurikubiwako",
    "JR京都線":     "kyoto",
    "京都線":       "kyoto",
    "JR神戸線":     "kobesanyo",
    "神戸線":       "kobesanyo",
    "山陽線":       "kobesanyo",
    "赤穂線":       "ako",
    "湖西線":       "kosei",
    "奈良線":       "nara",
    "嵯峨野線":     "sagano",
    "山陰線":       "sanin",
    "おおさか東線": "osakahigashi",
    "JR宝塚線":     "takarazuka",
    "宝塚線":       "takarazuka",
    "JR東西線":     "tozai",
    "東西線":       "tozai",
    "学研都市線":   "gakkentoshi",
    "播但線":       "bantan",
    "舞鶴線":       "maizuru",
    "大阪環状線":   "osakaloop",
    "JRゆめ咲線":  "yumesaki",
    "ゆめ咲線":    "yumesaki",
    "大和路線":     "yamatoji",
    "阪和線":       "hanwa",
    "羽衣線":       "hanwa",
    "関西空港線":   "kansaikuko",
    "草津線":       "kusatsu",
    "福知山線":     "fukuchiyama",
    "加古川線":     "kakogawa",
}


def fetch_delayed_lines(target_date: date) -> set[str]:
    """
    近畿エリア運行情報履歴ページから
    target_date に遅延が発生した路線IDセットを返す。

    Args:
        target_date: 遅延を確認する日付（通常は前日）

    Returns:
        遅延が発生した路線IDのセット (例: {"kyoto", "osakaloop"})

    Raises:
        requests.RequestException: ネットワークエラー時
    """
    html = _fetch_html(HISTORY_URL)
    return _parse_delayed_lines(html, target_date)


# ---------------------------------------------------------------------------
# 内部実装
# ---------------------------------------------------------------------------

def _fetch_html(url: str) -> str:
    """指定URLのHTMLを取得する。"""
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )
    }
    response = requests.get(url, headers=headers, timeout=30)
    response.raise_for_status()
    response.encoding = response.apparent_encoding
    return response.text


def _has_class_prefix(tag, prefix: str) -> bool:
    """タグのクラスリストに指定プレフィックスで始まるクラスが含まれるか判定する。"""
    return any(c.startswith(prefix) for c in tag.get("class", []))


def _parse_delayed_lines(html: str, target_date: date) -> set[str]:
    """
    履歴ページのHTMLをパースして target_date に遅延した路線IDセットを返す。

    【HTML構造】
      role="tabpanel" + class="KinkiHistory_tabContent__*"  ← タブパネル（京阪神・和歌山・北近畿）
        └─ div[class^="HistoryListTable_daily__"]           ← 1日分のブロック
             ├─ div[class^="HistoryListTable_dailyDateCell__"]  日付（インシデントあり）
             │   OR div[class^="HistoryListTable_dateCell__"]   日付（インシデントなし）
             └─ a[href*="kinki_history_detail"]             ← インシデントリンク

    クラス名は CSS Modules ハッシュを含むため、プレフィックスマッチで取得する。
    アクセシビリティ属性 role="tabpanel" を優先セレクタとして使用する。
    """
    soup = BeautifulSoup(html, "html.parser")
    delayed_ids: set[str] = set()

    # アクセシビリティ属性 role="tabpanel" でタブパネルを取得し、
    # KinkiHistory_tabContent__ プレフィックスで近畿エリアのものに絞り込む
    tab_panels = [
        tag for tag in soup.find_all(role="tabpanel")
        if _has_class_prefix(tag, "KinkiHistory_tabContent__")
    ]

    for panel in tab_panels:
        # 1日分のブロックを取得
        daily_blocks = [
            div for div in panel.find_all("div")
            if _has_class_prefix(div, "HistoryListTable_daily__")
        ]

        for daily in daily_blocks:
            # 日付セルを取得（インシデントあり: dailyDateCell__ / なし: dateCell__）
            date_cell = next(
                (
                    div for div in daily.find_all("div")
                    if _has_class_prefix(div, "HistoryListTable_dailyDateCell__")
                    or _has_class_prefix(div, "HistoryListTable_dateCell__")
                ),
                None,
            )
            if date_cell is None:
                continue

            block_date = _parse_date_text(date_cell.get_text(strip=True))
            if block_date != target_date:
                continue

            # 対象日のインシデントリンクを処理
            for link in daily.find_all("a", href=lambda h: h and "kinki_history_detail" in h):
                title = link.get_text(strip=True)
                route_name = _extract_route_name(title)
                if route_name:
                    line_id = ROUTE_NAME_TO_ID.get(route_name)
                    if line_id:
                        delayed_ids.add(line_id)
                    else:
                        logger.warning("未登録の路線名: %s", route_name)

    return delayed_ids


def _parse_date_text(text: str) -> date | None:
    """
    「3月9日（土）」などの日本語日付テキストを date オブジェクトに変換する。

    年が含まれない場合は当年を使用する。
    1月に12月の日付が出た場合（年末年始）は前年として扱う。

    Args:
        text: 日付を含むテキスト (例: "3月9日（土）", "2024年3月9日")

    Returns:
        パース成功時は date オブジェクト、失敗時は None
    """
    # 「YYYY年M月D日」形式
    m = re.search(r"(\d{4})年(\d{1,2})月(\d{1,2})日", text)
    if m:
        return date(int(m.group(1)), int(m.group(2)), int(m.group(3)))

    # 「M月D日」形式（年なし）
    m = re.search(r"(\d{1,2})月(\d{1,2})日", text)
    if m:
        month, day = int(m.group(1)), int(m.group(2))
        today = date.today()
        year = today.year
        # 1月に12月の日付が来た場合は前年扱い（年末年始ページ更新タイミング対策）
        if today.month == 1 and month == 12:
            year -= 1
        try:
            return date(year, month, day)
        except ValueError:
            return None

    return None


def _extract_route_name(text: str) -> str | None:
    """
    「【奈良線】 踏切の確認 列車の遅れ」などのテキストから
    【】内の路線名を抽出する。

    Args:
        text: インシデントタイトルテキスト

    Returns:
        路線名文字列 (例: "奈良線")、見つからなければ None
    """
    m = re.search(r"【(.+?)】", text)
    if m is None:
        return None
    return unicodedata.normalize("NFKC", m.group(1))
