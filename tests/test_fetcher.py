"""fetcher.py のユニットテスト"""

import sys
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fetcher import (
    AREAS,
    _fetch_area_master,
    _fetch_area_trafficinfo,
    fetch_all_line_ids,
    fetch_delayed_lines,
)


class TestFetchAreaTrafficinfo:
    def test_平常時_空セットを返す(self):
        with patch("fetcher._get_json") as mock:
            mock.return_value = {"lines": {}, "express": {}}
            result = _fetch_area_trafficinfo("kinki")
        assert result == set()

    def test_遅延あり_路線IDセットを返す(self):
        with patch("fetcher._get_json") as mock:
            mock.return_value = {
                "lines": {
                    "kobesanyo": {"info": "遅延", "detail": "..."},
                    "bantan": {"info": "運転見合わせ", "detail": "..."},
                },
                "express": {},
            }
            result = _fetch_area_trafficinfo("kinki")
        assert result == {"kobesanyo", "bantan"}

    def test_正しいURLを呼ぶ(self):
        with patch("fetcher._get_json") as mock:
            mock.return_value = {"lines": {}}
            _fetch_area_trafficinfo("chugoku")
        mock.assert_called_once_with(
            "https://www.train-guide.westjr.co.jp/api/v3/area_chugoku_trafficinfo.json"
        )


class TestFetchAreaMaster:
    def test_路線リストを返す(self):
        with patch("fetcher._get_json") as mock:
            mock.return_value = {
                "line": [
                    {"id": "kobesanyo", "name": "JR神戸線・山陽線"},
                    {"id": "kyoto", "name": "JR京都線"},
                ]
            }
            result = _fetch_area_master("kinki")
        assert result == [
            {"id": "kobesanyo", "name": "JR神戸線・山陽線"},
            {"id": "kyoto", "name": "JR京都線"},
        ]

    def test_idまたはnameがない要素はスキップ(self):
        with patch("fetcher._get_json") as mock:
            mock.return_value = {
                "line": [
                    {"id": "kobesanyo", "name": "JR神戸線・山陽線"},
                    {"id": "no-name-line"},  # name なし
                    {"name": "no-id-line"},  # id なし
                ]
            }
            result = _fetch_area_master("kinki")
        assert len(result) == 1
        assert result[0]["id"] == "kobesanyo"


class TestFetchDelayedLines:
    def test_複数エリアの遅延をマージ(self):
        def side_effect(area):
            return {
                "kinki": {"kobesanyo"},
                "chugoku": {"bantan"},
                "hokuriku": set(),
                "shinkansen": set(),
            }[area]

        with patch("fetcher._fetch_area_trafficinfo", side_effect=side_effect):
            result = fetch_delayed_lines()
        assert result == {"kobesanyo", "bantan"}

    def test_エリアのHTTPエラーはスキップ(self):
        import requests

        def side_effect(area):
            if area == "hokuriku":
                raise requests.HTTPError("404")
            return set()

        with patch("fetcher._fetch_area_trafficinfo", side_effect=side_effect):
            result = fetch_delayed_lines()
        assert isinstance(result, set)


class TestFetchAllLineIds:
    def test_重複IDを除去して返す(self):
        def side_effect(area):
            # kinki と chugoku で kobesanyo が重複
            return {
                "kinki": [
                    {"id": "kobesanyo", "name": "JR神戸線・山陽線"},
                    {"id": "kyoto", "name": "JR京都線"},
                ],
                "chugoku": [
                    {"id": "kobesanyo", "name": "JR神戸線・山陽線"},
                    {"id": "bantan", "name": "播但線"},
                ],
                "hokuriku": [],
                "shinkansen": [],
            }[area]

        with patch("fetcher._fetch_area_master", side_effect=side_effect):
            result = fetch_all_line_ids()

        ids = [r["id"] for r in result]
        assert ids.count("kobesanyo") == 1  # 重複なし
        assert "kyoto" in ids
        assert "bantan" in ids
