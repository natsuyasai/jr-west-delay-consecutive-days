"""counter.py のユニットテスト"""

from datetime import date

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from counter import get_delayed_lines, update_consecutive_days
from storage import AppState, LineState


def _make_state(lines: list[LineState]) -> AppState:
    return AppState(last_updated=date(2024, 3, 8), lines=lines)


class TestUpdateConsecutiveDays:
    def test_遅延あり_初日(self):
        state = _make_state([LineState(id="kyoto-kobe", name="JR京都線・神戸線")])
        result = update_consecutive_days(state, {"kyoto-kobe"}, date(2024, 3, 9))
        line = result.lines[0]
        assert line.consecutive_days == 1
        assert line.start_date == date(2024, 3, 9)

    def test_遅延あり_継続(self):
        state = _make_state([
            LineState(
                id="kyoto-kobe",
                name="JR京都線・神戸線",
                consecutive_days=3,
                start_date=date(2024, 3, 6),
            )
        ])
        result = update_consecutive_days(state, {"kyoto-kobe"}, date(2024, 3, 9))
        line = result.lines[0]
        assert line.consecutive_days == 4
        assert line.start_date == date(2024, 3, 6)  # 開始日は変わらない

    def test_遅延なし_リセット(self):
        state = _make_state([
            LineState(
                id="kyoto-kobe",
                name="JR京都線・神戸線",
                consecutive_days=5,
                start_date=date(2024, 3, 4),
            )
        ])
        result = update_consecutive_days(state, set(), date(2024, 3, 9))
        line = result.lines[0]
        assert line.consecutive_days == 0
        assert line.start_date is None

    def test_複数路線_混在(self):
        state = _make_state([
            LineState(id="kyoto-kobe", name="JR京都線・神戸線", consecutive_days=2, start_date=date(2024, 3, 7)),
            LineState(id="osaka-loop", name="大阪環状線", consecutive_days=0),
        ])
        result = update_consecutive_days(state, {"osaka-loop"}, date(2024, 3, 9))
        kyoto_kobe = next(l for l in result.lines if l.id == "kyoto-kobe")
        osaka_loop = next(l for l in result.lines if l.id == "osaka-loop")
        assert kyoto_kobe.consecutive_days == 0
        assert osaka_loop.consecutive_days == 1

    def test_last_updated更新(self):
        state = _make_state([LineState(id="kyoto-kobe", name="JR京都線・神戸線")])
        result = update_consecutive_days(state, set(), date(2024, 3, 9))
        assert result.last_updated == date(2024, 3, 9)


class TestGetDelayedLines:
    def test_遅延中路線のみ返す(self):
        state = _make_state([
            LineState(id="kyoto-kobe", name="JR京都線・神戸線", consecutive_days=3),
            LineState(id="osaka-loop", name="大阪環状線", consecutive_days=0),
            LineState(id="hanwa", name="阪和線", consecutive_days=1),
        ])
        result = get_delayed_lines(state)
        ids = [l.id for l in result]
        assert "kyoto-kobe" in ids
        assert "hanwa" in ids
        assert "osaka-loop" not in ids

    def test_遅延なしは空リスト(self):
        state = _make_state([LineState(id="kyoto-kobe", name="JR京都線・神戸線")])
        assert get_delayed_lines(state) == []
