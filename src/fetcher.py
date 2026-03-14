"""
JR西日本 京阪神エリア 遅延証明書履歴取得モジュール

各路線の履歴ページをスクレイピングして
指定日に遅延が発生した路線IDのセットを返す。

データソース:
  https://delay.trafficinfo.westjr.co.jp/pc/history/2/{url_id}
  過去45日間の遅延証明書履歴が掲載されている。
  日付行に <a> リンクがあれば遅延あり、なければ「掲載はありません」。
"""

from __future__ import annotations

import logging
import re
from datetime import date

from bs4 import BeautifulSoup
from playwright.sync_api import sync_playwright

logger = logging.getLogger(__name__)

_BASE_HISTORY_URL = "https://delay.trafficinfo.westjr.co.jp/pc/history/2/{url_id}"

# 京阪神エリア（area=2）の路線設定
# url_id: 履歴URLの末尾ID (/pc/history/2/{url_id})
# internal_id: storage.py の KINKI_LINES id と一致
KINKI_LINE_CONFIGS: list[dict] = [
    {"url_id": 2,  "internal_id": "hokurikubiwako"},
    {"url_id": 3,  "internal_id": "kyoto"},
    {"url_id": 4,  "internal_id": "kobesanyo"},
    {"url_id": 5,  "internal_id": "ako"},
    {"url_id": 6,  "internal_id": "kosei"},
    {"url_id": 7,  "internal_id": "kusatsu"},
    {"url_id": 8,  "internal_id": "nara"},
    {"url_id": 9,  "internal_id": "sagano"},
    {"url_id": 10, "internal_id": "osakahigashi"},
    {"url_id": 11, "internal_id": "takarazuka"},
    {"url_id": 12, "internal_id": "tozai"},
    {"url_id": 13, "internal_id": "gakkentoshi"},
    {"url_id": 14, "internal_id": "osakaloop"},
    {"url_id": 15, "internal_id": "yumesaki"},
    {"url_id": 16, "internal_id": "yamatoji"},
    {"url_id": 17, "internal_id": "hanwa"},
    {"url_id": 18, "internal_id": "hagoromo"},
    {"url_id": 19, "internal_id": "kansaikuko"},
    {"url_id": 20, "internal_id": "wakayama"},
    {"url_id": 21, "internal_id": "manyomahora"},
    {"url_id": 22, "internal_id": "kansai"},
    {"url_id": 48, "internal_id": "wadamisaki"},
    {"url_id": 49, "internal_id": "kakogawa"},
    {"url_id": 50, "internal_id": "hishin"},
]


def fetch_delayed_lines(target_date: date) -> set[str]:
    """
    京阪神エリア全路線の履歴ページを巡回し、
    target_date に遅延が発生した路線IDセットを返す。

    Args:
        target_date: 遅延を確認する日付（通常は前日）

    Returns:
        遅延が発生した路線IDのセット (例: {"kyoto", "osakaloop"})

    Raises:
        requests.RequestException: ネットワークエラー時
    """
    delayed_ids: set[str] = set()
    for config in KINKI_LINE_CONFIGS:
        url = _BASE_HISTORY_URL.format(url_id=config["url_id"])
        try:
            html = _fetch_html(url)
        except Exception:
            logger.exception("履歴ページ取得失敗: url_id=%s", config["url_id"])
            continue
        if _has_delay_on_date(html, target_date):
            delayed_ids.add(config["internal_id"])
    return delayed_ids


# ---------------------------------------------------------------------------
# 内部実装
# ---------------------------------------------------------------------------

def _fetch_html(url: str) -> str:
    """Playwright でJS実行後のHTMLを取得する。"""
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(url, wait_until="networkidle")
        html = page.content()
        browser.close()
    return html


def _has_delay_on_date(html: str, target_date: date) -> bool:
    """
    履歴ページのHTMLをパースして target_date に遅延があったか判定する。

    【HTML構造】
      table > tbody > tr
        - 1列目 td: 日付テキスト (例: "3月13日(金)")
        - 2列目以降 td: 時間帯別遅延状況
          - 遅延あり: <a href="/pc/delay-certificate/history/...">10分</a>
          - 遅延なし: "掲載はありません" テキスト

    target_date の行に <a> リンクが1つでもあれば True を返す。
    """
    soup = BeautifulSoup(html, "html.parser")
    for row in soup.select("table tbody tr"):
        cells = row.find_all(["td", "th"])
        if not cells:
            continue
        row_date = _parse_date_text(cells[0].get_text(strip=True))
        if row_date is None or row_date != target_date:
            continue
        # 対象日の行が見つかった — 時間帯セルにリンクがあれば遅延あり
        return any(cell.find("a") is not None for cell in cells[1:])
    return False


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
