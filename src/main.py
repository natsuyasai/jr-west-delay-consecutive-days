"""
JR西日本 近畿エリア 遅延連続日数カウンター - エントリーポイント

毎日朝4時にcronで実行し、前日の近畿エリア運行情報履歴から
各路線の連続遅延日数を更新・Xに投稿する。
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

from counter import get_delayed_lines, get_no_delay_lines, update_consecutive_days
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

    # 1. 状態ファイルを読み込む（存在しない場合は KINKI_LINES で初期化）
    state = load_state(DEFAULT_STATE_PATH)

    # 2. 前日の近畿エリア遅延路線を履歴ページから取得
    logger.info("遅延情報を取得中...")
    try:
        delayed_line_ids = fetch_delayed_lines(target_date)
    except Exception:
        logger.exception("遅延情報の取得に失敗しました")
        sys.exit(1)
    logger.info("遅延路線数: %d", len(delayed_line_ids))

    # 3. 連続日数を更新
    updated_state = update_consecutive_days(state, delayed_line_ids, target_date)

    # 4. 状態を保存
    save_state(DEFAULT_STATE_PATH, updated_state)
    logger.info("状態ファイルを保存しました")

    # 5. Xに投稿
    delayed_lines = get_delayed_lines(updated_state)
    no_delay_lines = get_no_delay_lines(updated_state)
    logger.info("遅延中路線: %s", [l.name for l in delayed_lines])
    logger.info("遅延なし路線: %s", [l.name for l in no_delay_lines])
    try:
        post_summary(delayed_lines, no_delay_lines, target_date)
        logger.info("Xへの投稿が完了しました")
    except Exception:
        logger.exception("Xへの投稿に失敗しました")
        sys.exit(1)


if __name__ == "__main__":
    main()
