"""
JR西日本 遅延連続日数カウンター - エントリーポイント

毎日朝4時にcronで実行し、当日の遅延情報（trafficinfo）を取得して
各路線の連続日数を更新・Xに投稿する。

実行タイミングについて:
  trafficinfo API は JR西日本が運行障害を公式アナウンスした路線を返す。
  朝4時実行により、深夜から早朝にかけての障害を当日分としてカウントする。
  前日昼間の障害がすでに解消済みの場合は検知されない点に注意。
"""

from __future__ import annotations

import logging
import os
import sys
from datetime import date, timedelta
from pathlib import Path

from dotenv import load_dotenv

from counter import get_delayed_lines, update_consecutive_days
from fetcher import fetch_all_line_ids, fetch_delayed_lines
from poster import post_summary
from storage import FALLBACK_LINES, build_initial_state, load_state, save_state

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

    # 1. 状態ファイルを読み込む（存在しない場合は初期化）
    state = _load_or_initialize_state(DEFAULT_STATE_PATH)

    # 2. JR西日本から遅延路線を取得
    logger.info("遅延情報を取得中...")
    try:
        delayed_line_ids = fetch_delayed_lines()
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


def _load_or_initialize_state(path: Path):
    """
    状態ファイルを読み込む。

    ファイルが存在しない場合（初回実行）は area_master API から
    路線リストを取得して初期状態を生成する。
    API取得失敗時は FALLBACK_LINES で代替する。
    """
    if path.exists():
        return load_state(path)

    logger.info("状態ファイルが存在しません。初回初期化を実行します")
    try:
        line_defs = fetch_all_line_ids()
        logger.info("master APIから%d路線を取得しました", len(line_defs))
    except Exception:
        logger.warning("master API取得失敗。フォールバック路線リストを使用します")
        line_defs = FALLBACK_LINES

    return build_initial_state(line_defs)


if __name__ == "__main__":
    main()
