"""storage.py のユニットテスト"""

import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from storage import KINKI_LINES, AppState, LineState, build_initial_state, load_state, save_state


class TestLoadState:
    def test_ファイルなし_KINKI_LINESで初期状態を返す(self, tmp_path):
        state = load_state(tmp_path / "nonexistent.yaml")
        assert len(state.lines) == len(KINKI_LINES)
        assert all(l.consecutive_days == 0 for l in state.lines)
        assert state.last_updated is None

    def test_ファイルあり_正常読み込み(self, tmp_path):
        yaml_path = tmp_path / "state.yaml"
        yaml_path.write_text(
            "last_updated: 2024-03-08\n"
            "lines:\n"
            "  - id: kyoto\n"
            "    name: JR京都線\n"
            "    consecutive_days: 3\n"
            "    start_date: 2024-03-06\n",
            encoding="utf-8",
        )
        state = load_state(yaml_path)
        assert state.last_updated == date(2024, 3, 8)
        assert len(state.lines) == 1
        assert state.lines[0].consecutive_days == 3
        assert state.lines[0].start_date == date(2024, 3, 6)

    def test_空ファイル_初期状態を返す(self, tmp_path):
        yaml_path = tmp_path / "state.yaml"
        yaml_path.write_text("", encoding="utf-8")
        state = load_state(yaml_path)
        assert len(state.lines) == len(KINKI_LINES)


class TestSaveState:
    def test_保存して読み込み_往復(self, tmp_path):
        yaml_path = tmp_path / "state.yaml"
        original = AppState(
            last_updated=date(2024, 3, 9),
            lines=[
                LineState(
                    id="kyoto",
                    name="JR京都線",
                    consecutive_days=5,
                    start_date=date(2024, 3, 4),
                ),
                LineState(id="osakaloop", name="大阪環状線"),
            ],
        )
        save_state(yaml_path, original)
        loaded = load_state(yaml_path)

        assert loaded.last_updated == date(2024, 3, 9)
        assert len(loaded.lines) == 2
        kyoto = next(l for l in loaded.lines if l.id == "kyoto")
        assert kyoto.consecutive_days == 5
        assert kyoto.start_date == date(2024, 3, 4)

    def test_ディレクトリが存在しない場合も保存できる(self, tmp_path):
        yaml_path = tmp_path / "nested" / "dir" / "state.yaml"
        state = AppState(lines=[LineState(id="kobesanyo", name="JR神戸線・山陽線")])
        save_state(yaml_path, state)
        assert yaml_path.exists()


class TestBuildInitialState:
    def test_KINKI_LINESで初期化(self):
        state = build_initial_state()
        assert len(state.lines) == len(KINKI_LINES)
        assert all(l.consecutive_days == 0 for l in state.lines)
        assert all(l.start_date is None for l in state.lines)
        assert state.last_updated is None

    def test_全路線のidとnameが設定済み(self):
        state = build_initial_state()
        for line in state.lines:
            assert line.id
            assert line.name
