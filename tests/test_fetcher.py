"""fetcher.py のユニットテスト"""

import sys
from datetime import date
from pathlib import Path
from unittest.mock import patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fetcher import (
    ROUTE_NAME_TO_ID,
    _extract_route_name,
    _parse_date_text,
    _parse_delayed_lines,
    fetch_delayed_lines,
)


class TestParseDateText:
    def test_月日形式(self):
        with patch("fetcher.date") as mock_date:
            mock_date.today.return_value = date(2024, 3, 10)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            result = _parse_date_text("3月9日（土）")
        assert result == date(2024, 3, 9)

    def test_年月日形式(self):
        result = _parse_date_text("2024年3月9日")
        assert result == date(2024, 3, 9)

    def test_年月日形式_テキスト混在(self):
        result = _parse_date_text("更新日：2024年3月9日（土）")
        assert result == date(2024, 3, 9)

    def test_年末年始_1月に12月の日付(self):
        with patch("fetcher.date") as mock_date:
            mock_date.today.return_value = date(2025, 1, 1)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            result = _parse_date_text("12月31日（火）")
        assert result == date(2024, 12, 31)

    def test_日付なし_Noneを返す(self):
        assert _parse_date_text("運行情報なし") is None

    def test_空文字_Noneを返す(self):
        assert _parse_date_text("") is None


class TestExtractRouteName:
    def test_路線名を抽出(self):
        assert _extract_route_name("【奈良線】 踏切の確認 列車の遅れ") == "奈良線"

    def test_JRプレフィックスあり(self):
        assert _extract_route_name("【JR京都線】 人身事故 列車の遅れ") == "JR京都線"

    def test_全角JRをNFKC正規化(self):
        # 実際のHTMLに含まれる全角文字「ＪＲ宝塚線」→「JR宝塚線」
        assert _extract_route_name("【ＪＲ宝塚線】踏切内車立ち往生による列車の遅れ") == "JR宝塚線"

    def test_全角JR京都線をNFKC正規化(self):
        assert _extract_route_name("【ＪＲ京都線】お客様救護による列車の遅れ") == "JR京都線"

    def test_括弧なし_Noneを返す(self):
        assert _extract_route_name("奈良線 列車の遅れ") is None

    def test_空文字_Noneを返す(self):
        assert _extract_route_name("") is None


class TestRouteNameToId:
    def test_代表的な路線名が登録済み(self):
        assert ROUTE_NAME_TO_ID["JR京都線"] == "kyoto"
        assert ROUTE_NAME_TO_ID["大阪環状線"] == "osakaloop"
        assert ROUTE_NAME_TO_ID["山陰線"] == "sanin"

    def test_同一路線の別表記が同じIDに対応(self):
        assert ROUTE_NAME_TO_ID["北陸線"] == ROUTE_NAME_TO_ID["琵琶湖線"]
        assert ROUTE_NAME_TO_ID["JR神戸線"] == ROUTE_NAME_TO_ID["神戸線"]
        assert ROUTE_NAME_TO_ID["阪和線"] == ROUTE_NAME_TO_ID["羽衣線"]


def _make_history_html(days: list[tuple[str, list[str]]]) -> str:
    """
    テスト用の履歴ページHTMLを生成するヘルパー。

    Args:
        days: [(日付文字列, [インシデントタイトル, ...]), ...]
              インシデントリストが空のときは「履歴はありません。」の行になる。
    """
    rows = []
    for date_str, incidents in days:
        if incidents:
            date_cell = f'<div class="HistoryListTable_dailyDateCell__XXXXX">{date_str}</div>'
            incident_rows = "".join(
                f'<div class="HistoryListTable_historyRow__XXXXX">'
                f'<div class="HistoryListTable_bodyCellContainer__XXXXX">'
                f'<div class="HistoryListTable_dailyBodyCell__XXXXX">'
                f'<a class="HistoryListTable_link__XXXXX" href="/list/kinki_history_detail.html?trafficId=1">'
                f"{title}</a></div></div></div>"
                for title in incidents
            )
            rows.append(
                f'<div class="HistoryListTable_daily__XXXXX">'
                f'<div class="HistoryListTable_historyRow__XXXXX">{date_cell}<div></div></div>'
                f"{incident_rows}</div>"
            )
        else:
            rows.append(
                f'<div class="HistoryListTable_daily__XXXXX">'
                f'<div class="HistoryListTable_historyRow__XXXXX">'
                f'<div class="HistoryListTable_dateCell__XXXXX">{date_str}</div>'
                f'<div class="HistoryListTable_bodyCell__XXXXX">履歴はありません。</div>'
                f"</div></div>"
            )
    body = "".join(rows)
    return (
        f'<div role="tabpanel" class="KinkiHistory_tabContent__UIFL_">'
        f'<div class="HistoryListTable_table__XXXXX">{body}</div>'
        f"</div>"
    )


class TestParseDelayedLines:
    def test_対象日に遅延あり(self):
        html = _make_history_html([
            ("2026年03月10日", ["【草津線】動物と接触による列車の遅れ", "【湖西線】沿線の確認による列車の遅れ"]),
            ("2026年03月09日", ["【奈良線】車両の確認による列車の遅れ"]),
        ])
        result = _parse_delayed_lines(html, date(2026, 3, 10))
        assert result == {"kusatsu", "kosei"}

    def test_対象日に遅延なし_空セットを返す(self):
        html = _make_history_html([
            ("2026年03月08日", []),
        ])
        result = _parse_delayed_lines(html, date(2026, 3, 8))
        assert result == set()

    def test_対象日が存在しない_空セットを返す(self):
        html = _make_history_html([
            ("2026年03月10日", ["【奈良線】列車の遅れ"]),
        ])
        result = _parse_delayed_lines(html, date(2026, 3, 9))
        assert result == set()

    def test_全角JR路線名を正規化して取得(self):
        html = _make_history_html([
            ("2026年03月07日", ["【ＪＲ宝塚線】踏切内車立ち往生による列車の遅れ"]),
        ])
        result = _parse_delayed_lines(html, date(2026, 3, 7))
        assert result == {"takarazuka"}

    def test_複数タブパネルを横断して集計(self):
        # 同じ日付が2つのタブパネルにある場合（京阪神 + 和歌山エリアなど）
        panel1 = (
            '<div role="tabpanel" class="KinkiHistory_tabContent__AAA">'
            '<div class="HistoryListTable_daily__XXX">'
            '<div class="HistoryListTable_historyRow__XXX">'
            '<div class="HistoryListTable_dailyDateCell__XXX">2026年03月10日</div><div></div>'
            '</div>'
            '<div class="HistoryListTable_historyRow__XXX">'
            '<div class="HistoryListTable_bodyCellContainer__XXX">'
            '<div class="HistoryListTable_dailyBodyCell__XXX">'
            '<a href="/list/kinki_history_detail.html?trafficId=1">【奈良線】列車の遅れ</a>'
            '</div></div></div>'
            '</div></div>'
        )
        panel2 = (
            '<div role="tabpanel" class="KinkiHistory_tabContent__BBB">'
            '<div class="HistoryListTable_daily__XXX">'
            '<div class="HistoryListTable_historyRow__XXX">'
            '<div class="HistoryListTable_dailyDateCell__XXX">2026年03月10日</div><div></div>'
            '</div>'
            '<div class="HistoryListTable_historyRow__XXX">'
            '<div class="HistoryListTable_bodyCellContainer__XXX">'
            '<div class="HistoryListTable_dailyBodyCell__XXX">'
            '<a href="/list/kinki_history_detail.html?trafficId=2">【阪和線】列車の遅れ</a>'
            '</div></div></div>'
            '</div></div>'
        )
        result = _parse_delayed_lines(panel1 + panel2, date(2026, 3, 10))
        assert result == {"nara", "hanwa"}

    def test_roleがtabpanelでない要素は無視される(self):
        # KinkiHistory_tabContent__ クラスを持つが role がない要素は無視
        html = (
            '<div class="KinkiHistory_tabContent__UIFL_">'
            '<div class="HistoryListTable_daily__XXX">'
            '<div class="HistoryListTable_historyRow__XXX">'
            '<div class="HistoryListTable_dailyDateCell__XXX">2026年03月10日</div><div></div>'
            '</div>'
            '<div class="HistoryListTable_historyRow__XXX">'
            '<div class="HistoryListTable_bodyCellContainer__XXX">'
            '<div class="HistoryListTable_dailyBodyCell__XXX">'
            '<a href="/list/kinki_history_detail.html?trafficId=1">【奈良線】列車の遅れ</a>'
            '</div></div></div>'
            '</div></div>'
        )
        result = _parse_delayed_lines(html, date(2026, 3, 10))
        assert result == set()

    def test_空HTML_空セットを返す(self):
        assert _parse_delayed_lines("", date(2026, 3, 10)) == set()


class TestFetchDelayedLines:
    def test_fetch_htmlが呼ばれる(self):
        with patch("fetcher._fetch_html", return_value="<html></html>") as mock_fetch:
            with patch("fetcher._parse_delayed_lines", return_value=set()):
                fetch_delayed_lines(date(2024, 3, 9))
        mock_fetch.assert_called_once()

    def test_parse_delayed_linesにtarget_dateが渡される(self):
        target = date(2024, 3, 9)
        with patch("fetcher._fetch_html", return_value="<html></html>"):
            with patch("fetcher._parse_delayed_lines", return_value=set()) as mock_parse:
                fetch_delayed_lines(target)
        _, called_date = mock_parse.call_args.args
        assert called_date == target

    def test_戻り値がsetである(self):
        with patch("fetcher._fetch_html", return_value="<html></html>"):
            with patch("fetcher._parse_delayed_lines", return_value={"kyoto", "nara"}):
                result = fetch_delayed_lines(date(2024, 3, 9))
        assert result == {"kyoto", "nara"}
