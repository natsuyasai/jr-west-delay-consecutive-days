"""fetcher.py のユニットテスト"""

import sys
from datetime import date
from pathlib import Path
from unittest.mock import call, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fetcher import (
    KINKI_LINE_CONFIGS,
    _has_delay_on_date,
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


def _make_route_history_html(rows: list[tuple[str, bool]]) -> str:
    """
    テスト用の路線別履歴ページHTMLを生成するヘルパー。

    Args:
        rows: [(日付文字列, 遅延あり), ...]
    """
    tr_rows = []
    for date_str, has_delay in rows:
        if has_delay:
            cells = (
                f"<td>{date_str}</td>"
                '<td><a href="/pc/delay-certificate/history/2/3/2026-03-13/3">10分</a></td>'
                "<td>掲載はありません</td>"
            )
        else:
            cells = (
                f"<td>{date_str}</td>"
                "<td>掲載はありません</td>"
                "<td>掲載はありません</td>"
            )
        tr_rows.append(f"<tr>{cells}</tr>")
    tbody = "".join(tr_rows)
    return (
        "<table>"
        "<thead><tr><th>日付</th><th>始発～7:00</th><th>7:00～9:00</th></tr></thead>"
        f"<tbody><tr></tr>{tbody}</tbody>"
        "</table>"
    )


class TestHasDelayOnDate:
    def test_対象日に遅延あり_Trueを返す(self):
        html = _make_route_history_html([
            ("3月13日(金)", True),
            ("3月12日(木)", False),
        ])
        with patch("fetcher.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 14)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            result = _has_delay_on_date(html, date(2026, 3, 13))
        assert result is True

    def test_対象日に遅延なし_Falseを返す(self):
        html = _make_route_history_html([
            ("3月13日(金)", False),
        ])
        with patch("fetcher.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 14)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            result = _has_delay_on_date(html, date(2026, 3, 13))
        assert result is False

    def test_対象日が存在しない_Falseを返す(self):
        html = _make_route_history_html([
            ("3月13日(金)", True),
        ])
        with patch("fetcher.date") as mock_date:
            mock_date.today.return_value = date(2026, 3, 14)
            mock_date.side_effect = lambda *a, **kw: date(*a, **kw)
            result = _has_delay_on_date(html, date(2026, 3, 12))
        assert result is False

    def test_年月日形式の日付(self):
        html = _make_route_history_html([
            ("2026年3月13日", True),
        ])
        result = _has_delay_on_date(html, date(2026, 3, 13))
        assert result is True

    def test_テーブルなし_Falseを返す(self):
        assert _has_delay_on_date("<html></html>", date(2026, 3, 13)) is False

    def test_空HTML_Falseを返す(self):
        assert _has_delay_on_date("", date(2026, 3, 13)) is False


class TestFetchDelayedLines:
    def test_全路線のURLを取得する(self):
        with patch("fetcher._fetch_html", return_value="<html></html>") as mock_fetch:
            fetch_delayed_lines(date(2026, 3, 13))
        assert mock_fetch.call_count == len(KINKI_LINE_CONFIGS)

    def test_遅延路線のIDを返す(self):
        def fake_fetch(url: str) -> str:
            # url_id=3 (kyoto) のみ遅延ありのHTMLを返す
            if url.endswith("/3"):
                return _make_route_history_html([("2026年3月13日", True)])
            return _make_route_history_html([("2026年3月13日", False)])

        with patch("fetcher._fetch_html", side_effect=fake_fetch):
            result = fetch_delayed_lines(date(2026, 3, 13))
        assert "kyoto" in result

    def test_取得失敗路線はスキップされる(self):
        import requests as req

        call_count = 0

        def fake_fetch(url: str) -> str:
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise req.RequestException("timeout")
            return _make_route_history_html([("2026年3月13日", False)])

        with patch("fetcher._fetch_html", side_effect=fake_fetch):
            result = fetch_delayed_lines(date(2026, 3, 13))
        assert isinstance(result, set)

    def test_戻り値がsetである(self):
        with patch("fetcher._fetch_html", return_value="<html></html>"):
            result = fetch_delayed_lines(date(2026, 3, 13))
        assert isinstance(result, set)
