"""fetcher.py のユニットテスト"""

import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from fetcher import _parse_delayed_lines, LINE_NAME_TO_ID


class TestParseDelayedLines:
    def test_遅延路線を検出(self):
        # NOTE: 実際のHTML構造が判明したらテストを更新すること
        html = """
        <html><body>
          <div class="train-info-delay">JR京都線 遅延中</div>
          <div class="train-info-delay">大阪環状線 運転見合わせ</div>
        </body></html>
        """
        result = _parse_delayed_lines(html)
        assert "kyoto-kobe" in result
        assert "osaka-loop" in result

    def test_遅延なしは空セット(self):
        html = "<html><body><p>平常運転中</p></body></html>"
        result = _parse_delayed_lines(html)
        assert result == set()

    def test_IDマッピングの確認(self):
        # 全ての路線名がIDにマッピングされていること
        assert LINE_NAME_TO_ID["山陽新幹線"] == "sanyo-shinkansen"
        assert LINE_NAME_TO_ID["JR京都線"] == "kyoto-kobe"
        assert LINE_NAME_TO_ID["大阪環状線"] == "osaka-loop"
