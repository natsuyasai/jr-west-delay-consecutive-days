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


def _parse_delayed_lines(html: str, target_date: date) -> set[str]:
    """
    履歴ページのHTMLをパースして target_date に遅延した路線IDセットを返す。

    【実装手順】
    1. ブラウザの開発者ツール（F12）で kinki_history.html の構造を確認する
    2. 日付グループのHTML要素・クラス名を特定する
    3. 各インシデントリンクのHTML要素・クラス名を特定する
    4. 以下のTODOを実際のセレクタに置き換える

    【想定HTML構造（要確認）】
      日付ヘッダー要素に「3月9日（土）」のような日付テキスト
      その配下に <a href="kinki_history_detail.html?id=..."> が並ぶ
      リンクテキストが「【奈良線】 踏切の確認 列車の遅れ」などの形式

    【参考】
      詳細ページ例: https://trafficinfo.westjr.co.jp/kinki_history_detail.html?id=00112599
    """
    soup = BeautifulSoup(html, "html.parser")
    delayed_ids: set[str] = set()

    # TODO: 実際のページHTML構造を開発者ツールで確認してセレクタを実装する
    #
    # 実装イメージ:
    #
    #   current_date = None
    #   for section in soup.select("適切なセレクタ"):
    #       # 日付ヘッダーテキストから日付をパース
    #       date_text = section.select_one("日付要素のセレクタ").get_text(strip=True)
    #       current_date = _parse_date_text(date_text)
    #
    #       if current_date != target_date:
    #           continue
    #
    #       # 当日のインシデントリンクを処理
    #       for link in section.select("インシデントリンクのセレクタ"):
    #           title = link.get_text(strip=True)
    #           route_name = _extract_route_name(title)
    #           if route_name:
    #               line_id = ROUTE_NAME_TO_ID.get(route_name)
    #               if line_id:
    #                   delayed_ids.add(line_id)
    #               else:
    #                   logger.warning("未登録の路線名: %s", route_name)

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
    return m.group(1) if m else None
