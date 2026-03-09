"""
X(Twitter)投稿モジュール

連続遅延日数のサマリーをXに投稿する。
"""

from __future__ import annotations

import os
from datetime import date

import tweepy

from storage import LineState


def post_summary(delayed_lines: list[LineState], target_date: date) -> None:
    """
    遅延中路線の連続日数サマリーをXに投稿する。

    遅延路線が0件の場合は投稿しない。

    Args:
        delayed_lines: 連続日数1以上の路線一覧
        target_date:   対象日付
    """
    if not delayed_lines:
        return

    text = _build_post_text(delayed_lines, target_date)
    _post_to_x(text)


def _build_post_text(delayed_lines: list[LineState], target_date: date) -> str:
    """投稿テキストを組み立てる。"""
    date_str = target_date.strftime("%Y/%m/%d")
    lines_text = "\n".join(_format_line(line) for line in delayed_lines)

    return (
        f"【JR西日本 遅延連続日数】{date_str}時点\n"
        f"\n"
        f"{lines_text}\n"
        f"\n"
        f"※前日に遅延が発生した路線を掲載"
    )


def _format_line(line: LineState) -> str:
    """1路線分の表示テキストを返す。"""
    if line.start_date and line.consecutive_days > 1:
        start_str = line.start_date.strftime("%-m/%-d")
        return f"{line.name}: {line.consecutive_days}日連続({start_str}〜)"
    return f"{line.name}: 1日"


def _post_to_x(text: str) -> None:
    """Xに投稿する。"""
    client = tweepy.Client(
        consumer_key=os.environ["X_API_KEY"],
        consumer_secret=os.environ["X_API_SECRET"],
        access_token=os.environ["X_ACCESS_TOKEN"],
        access_token_secret=os.environ["X_ACCESS_TOKEN_SECRET"],
    )
    client.create_tweet(text=text)
