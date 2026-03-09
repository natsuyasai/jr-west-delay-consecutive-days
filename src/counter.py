"""
連続日数カウントモジュール

路線ごとの連続遅延日数を更新するロジックを提供する。
"""

from __future__ import annotations

from datetime import date

from storage import LineState, AppState


def update_consecutive_days(
    state: AppState,
    delayed_line_ids: set[str],
    target_date: date,
) -> AppState:
    """
    前日の遅延情報をもとに各路線の連続日数を更新する。

    Args:
        state:            現在の状態 (YAMLから読み込んだデータ)
        delayed_line_ids: 遅延が発生した路線IDのセット
        target_date:      対象日付 (通常は前日)

    Returns:
        更新後の状態
    """
    updated_lines: list[LineState] = []

    for line in state.lines:
        if line.id in delayed_line_ids:
            # 遅延あり: 連続日数を増やす
            new_consecutive = line.consecutive_days + 1
            new_start = line.start_date if line.start_date else target_date
            updated_lines.append(
                LineState(
                    id=line.id,
                    name=line.name,
                    consecutive_days=new_consecutive,
                    start_date=new_start,
                )
            )
        else:
            # 遅延なし: リセット
            updated_lines.append(
                LineState(
                    id=line.id,
                    name=line.name,
                    consecutive_days=0,
                    start_date=None,
                )
            )

    return AppState(last_updated=target_date, lines=updated_lines)


def get_delayed_lines(state: AppState) -> list[LineState]:
    """連続日数が1以上の路線一覧を返す。"""
    return [line for line in state.lines if line.consecutive_days > 0]
