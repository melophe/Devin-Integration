"""Lambda Worker: Devin起動 → ポーリング → Redmineにコメント。"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.config import load
from app.devin import DevinClient
from app.prompt import build_prompt
from app.redmine import RedmineClient

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_TERMINAL = {"completed", "finished", "exit", "stopped", "failed", "error", "cancelled", "canceled", "suspended"}
_SUCCESS = {"completed", "finished", "exit"}
_POLL_INTERVAL = 180  # 3分
_POLL_MAX = 5         # 最大5回（15分）


def handler(event: dict[str, Any], context: Any) -> None:
    try:
        asyncio.run(_handle(event))
    except Exception as e:
        logger.exception("Workerエラー: %s", e)


async def _handle(event: dict[str, Any]) -> None:
    cfg = load()
    issue_id: int = event["issue_id"]
    mention_text: str = event.get("mention_text", "このチケットの内容を確認して対応してください")

    redmine = RedmineClient(cfg.redmine_url, cfg.redmine_api_key)
    devin = DevinClient(cfg.devin_api_key, cfg.devin_api_base)

    # チケット詳細取得
    issue = await redmine.get_issue(issue_id)

    # プロンプト生成
    prompt = build_prompt(issue, mention_text, cfg.default_template)
    logger.info("プロンプト生成完了 (issue #%s, %d文字)", issue_id, len(prompt))

    # Devin起動
    session = await devin.create_session(prompt)
    session_id: str = session.get("session_id", "unknown")

    await redmine.add_comment(issue_id, f"Devinを起動しました。\nSession ID: `{session_id}`")
    logger.info("Devin起動: issue #%s, session %s", issue_id, session_id)

    # ポーリング（3分×最大5回）
    for i in range(_POLL_MAX):
        await asyncio.sleep(_POLL_INTERVAL)
        status = await devin.get_session_status(session_id)
        logger.info("ポーリング %d回目: session %s status=%s", i + 1, session_id, status)

        if status.lower() in _TERMINAL:
            if status.lower() in _SUCCESS:
                comment = f"Devinの作業が完了しました。\nSession ID: `{session_id}`\nStatus: {status}"
            else:
                comment = f"Devinの作業が終了しました。\nSession ID: `{session_id}`\nStatus: {status}"
            await redmine.add_comment(issue_id, comment)
            return

    # タイムアウト
    await redmine.add_comment(issue_id, f"Devinの作業が15分以内に完了しませんでした。\nSession ID: `{session_id}`\nDevinの画面で確認してください。")
