"""fetcher.py のユニットテスト

NOTE: _parse_delayed_lines のHTMLパース部分は未実装（TODO）のため
      実際のページ構造が確認できてから追加する。
      ここでは実装済みのユーティリティ関数をテストする。
"""

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
