"""
JR西日本 遅延連続日数カウンター - エントリーポイント

毎日朝4時にcronで実行し、前日の遅延情報を取得して
各路線の連続日数を更新・Xに投稿する。
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

from counter import get_delayed_lines, update_consecutive_days
from fetcher import fetch_delayed_lines
from poster import post_summary
from storage import load_state, save_state

load_dotenv()

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
)
logger = logging.getLogger(__name__)

DEFAULT_STATE_PATH = Path(
    os.environ.get("STATE_FILE_PATH", "data/state.yaml")
)


def main() -> None:
    target_date = date.today() - timedelta(days=1)
    logger.info("対象日付: %s", target_date)

    # 1. JR西日本から遅延路線を取得
    logger.info("遅延情報を取得中...")
    try:
        delayed_line_ids = fetch_delayed_lines()
    except Exception:
        logger.exception("遅延情報の取得に失敗しました")
        sys.exit(1)
    logger.info("遅延路線数: %d", len(delayed_line_ids))

    # 2. 現在の状態を読み込む
    state = load_state(DEFAULT_STATE_PATH)
    logger.info("状態ファイルを読み込みました: %s", DEFAULT_STATE_PATH)

    # 3. 連続日数を更新
    updated_state = update_consecutive_days(state, delayed_line_ids, target_date)

    # 4. 状態を保存
    save_state(DEFAULT_STATE_PATH, updated_state)
    logger.info("状態ファイルを保存しました")

    # 5. Xに投稿
    delayed_lines = get_delayed_lines(updated_state)
    if delayed_lines:
        logger.info("遅延中路線: %s", [l.name for l in delayed_lines])
        try:
            post_summary(delayed_lines, target_date)
            logger.info("Xへの投稿が完了しました")
        except Exception:
            logger.exception("Xへの投稿に失敗しました")
            sys.exit(1)
    else:
        logger.info("遅延路線なし。投稿をスキップします")


if __name__ == "__main__":
    main()
