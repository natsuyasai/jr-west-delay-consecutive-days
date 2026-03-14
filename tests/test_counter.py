"""counter.py のユニットテスト"""

from datetime import date

import pytest
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from counter import get_delayed_lines, get_no_delay_lines, update_consecutive_days
from storage import AppState, LineState


def _make_state(lines: list[LineState]) -> AppState:
    return AppState(last_updated=date(2024, 3, 8), lines=lines)


class TestUpdateConsecutiveDays:
    def test_遅延あり_初日(self):
        state = _make_state([LineState(id="kyoto", name="JR京都線")])
        result = update_consecutive_days(state, {"kyoto"}, date(2024, 3, 9))
        line = result.lines[0]
        assert line.consecutive_days == 1
        assert line.start_date == date(2024, 3, 9)
        assert line.no_delay_consecutive_days == 0
        assert line.no_delay_start_date is None

    def test_遅延あり_継続(self):
        state = _make_state([
            LineState(
                id="kyoto",
                name="JR京都線",
                consecutive_days=3,
                start_date=date(2024, 3, 6),
            )
        ])
        result = update_consecutive_days(state, {"kyoto"}, date(2024, 3, 9))
        line = result.lines[0]
        assert line.consecutive_days == 4
        assert line.start_date == date(2024, 3, 6)  # 開始日は変わらない
        assert line.no_delay_consecutive_days == 0
        assert line.no_delay_start_date is None

    def test_遅延なし_初日(self):
        state = _make_state([LineState(id="kyoto", name="JR京都線")])
        result = update_consecutive_days(state, set(), date(2024, 3, 9))
        line = result.lines[0]
        assert line.consecutive_days == 0
        assert line.start_date is None
        assert line.no_delay_consecutive_days == 1
        assert line.no_delay_start_date == date(2024, 3, 9)

    def test_遅延なし_継続(self):
        state = _make_state([
            LineState(
                id="kyoto",
                name="JR京都線",
                no_delay_consecutive_days=5,
                no_delay_start_date=date(2024, 3, 4),
            )
        ])
        result = update_consecutive_days(state, set(), date(2024, 3, 9))
        line = result.lines[0]
        assert line.no_delay_consecutive_days == 6
        assert line.no_delay_start_date == date(2024, 3, 4)  # 開始日は変わらない
        assert line.consecutive_days == 0
        assert line.start_date is None

    def test_遅延あり_遅延なし連続日数をリセット(self):
        state = _make_state([
            LineState(
                id="kyoto",
                name="JR京都線",
                no_delay_consecutive_days=10,
                no_delay_start_date=date(2024, 2, 28),
            )
        ])
        result = update_consecutive_days(state, {"kyoto"}, date(2024, 3, 9))
        line = result.lines[0]
        assert line.consecutive_days == 1
        assert line.no_delay_consecutive_days == 0
        assert line.no_delay_start_date is None

    def test_遅延なし_遅延連続日数をリセット(self):
        state = _make_state([
            LineState(
                id="kyoto",
                name="JR京都線",
                consecutive_days=5,
                start_date=date(2024, 3, 4),
            )
        ])
        result = update_consecutive_days(state, set(), date(2024, 3, 9))
        line = result.lines[0]
        assert line.consecutive_days == 0
        assert line.start_date is None
        assert line.no_delay_consecutive_days == 1

    def test_複数路線_混在(self):
        state = _make_state([
            LineState(id="kyoto", name="JR京都線", consecutive_days=2, start_date=date(2024, 3, 7)),
            LineState(id="osakaloop", name="大阪環状線", no_delay_consecutive_days=3, no_delay_start_date=date(2024, 3, 6)),
        ])
        result = update_consecutive_days(state, {"osakaloop"}, date(2024, 3, 9))
        kyoto = next(l for l in result.lines if l.id == "kyoto")
        osaka = next(l for l in result.lines if l.id == "osakaloop")
        # kyoto: 遅延なし → 遅延連続をリセット、遅延なし連続を開始
        assert kyoto.consecutive_days == 0
        assert kyoto.no_delay_consecutive_days == 1
        # osakaloop: 遅延あり → 遅延連続を増加、遅延なし連続をリセット
        assert osaka.consecutive_days == 1
        assert osaka.no_delay_consecutive_days == 0
        assert osaka.no_delay_start_date is None

    def test_last_updated更新(self):
        state = _make_state([LineState(id="kyoto", name="JR京都線")])
        result = update_consecutive_days(state, set(), date(2024, 3, 9))
        assert result.last_updated == date(2024, 3, 9)


class TestGetDelayedLines:
    def test_遅延中路線のみ返す(self):
        state = _make_state([
            LineState(id="kyoto", name="JR京都線", consecutive_days=3),
            LineState(id="osakaloop", name="大阪環状線", consecutive_days=0, no_delay_consecutive_days=5),
            LineState(id="hanwa", name="阪和線", consecutive_days=1),
        ])
        result = get_delayed_lines(state)
        ids = [l.id for l in result]
        assert "kyoto" in ids
        assert "hanwa" in ids
        assert "osakaloop" not in ids

    def test_遅延なしは空リスト(self):
        state = _make_state([LineState(id="kyoto", name="JR京都線")])
        assert get_delayed_lines(state) == []


class TestGetNoDelayLines:
    def test_遅延なし路線のみ返す(self):
        state = _make_state([
            LineState(id="kyoto", name="JR京都線", consecutive_days=2),
            LineState(id="osakaloop", name="大阪環状線", no_delay_consecutive_days=5),
            LineState(id="hanwa", name="阪和線", no_delay_consecutive_days=1),
        ])
        result = get_no_delay_lines(state)
        ids = [l.id for l in result]
        assert "osakaloop" in ids
        assert "hanwa" in ids
        assert "kyoto" not in ids

    def test_全路線遅延中は空リスト(self):
        state = _make_state([LineState(id="kyoto", name="JR京都線", consecutive_days=3)])
        assert get_no_delay_lines(state) == []
