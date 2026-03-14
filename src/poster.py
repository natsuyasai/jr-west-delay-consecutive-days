"""
X(Twitter)投稿モジュール

連続遅延日数のサマリーをXに投稿する。
"""

from __future__ import annotations

import os
from datetime import date

import tweepy

from storage import LineState


def post_summary(
    delayed_lines: list[LineState],
    no_delay_lines: list[LineState],
    target_date: date,
) -> None:
    """
    遅延中路線・遅延なし路線の連続日数サマリーをXに投稿する。

    どちらのリストも空の場合は投稿しない。

    Args:
        delayed_lines:  遅延連続日数1以上の路線一覧
        no_delay_lines: 遅延なし連続日数1以上の路線一覧
        target_date:    対象日付
    """
    if not delayed_lines and not no_delay_lines:
        return

    text = _build_post_text(delayed_lines, no_delay_lines, target_date)
    _post_to_x(text)


def _build_post_text(
    delayed_lines: list[LineState],
    no_delay_lines: list[LineState],
    target_date: date,
) -> str:
    """投稿テキストを組み立てる。"""
    date_str = target_date.strftime("%Y/%m/%d")
    sections: list[str] = []

    if delayed_lines:
        delayed_text = "\n".join(_format_delay_line(line) for line in delayed_lines)
        sections.append(f"■ 遅延あり\n{delayed_text}")

    if no_delay_lines:
        no_delay_text = "\n".join(_format_no_delay_line(line) for line in no_delay_lines)
        sections.append(f"■ 遅延なし\n{no_delay_text}")

    body = "\n\n".join(sections)
    return (
        f"【JR西日本 連続日数】{date_str}時点\n"
        f"\n"
        f"{body}\n"
        f"\n"
        f"※前日の遅延証明書履歴をもとに集計"
    )


def _format_delay_line(line: LineState) -> str:
    """遅延あり路線1件分のテキストを返す。"""
    if line.start_date and line.consecutive_days > 1:
        start_str = "{}/{}".format(line.start_date.month, line.start_date.day)
        return f"{line.name}: {line.consecutive_days}日連続({start_str}〜)"
    return f"{line.name}: 1日"


def _format_no_delay_line(line: LineState) -> str:
    """遅延なし路線1件分のテキストを返す。"""
    if line.no_delay_start_date and line.no_delay_consecutive_days > 1:
        start_str = "{}/{}".format(line.no_delay_start_date.month, line.no_delay_start_date.day)
        return f"{line.name}: {line.no_delay_consecutive_days}日連続({start_str}〜)"
    return f"{line.name}: 1日"


def _post_to_x(text: str) -> None:
    """Xに投稿する。"""
    print(text)
    # TODO テスト中なので投稿部分はコメントアウト
    # client = tweepy.Client(
    #     consumer_key=os.environ["X_API_KEY"],
    #     consumer_secret=os.environ["X_API_SECRET"],
    #     access_token=os.environ["X_ACCESS_TOKEN"],
    #     access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    # )
    # client.create_tweet(text=text)
