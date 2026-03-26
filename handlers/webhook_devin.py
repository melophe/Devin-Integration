"""Lambda B: Devin完了Webhook受信 → Redmineにコメント追加。"""

from __future__ import annotations

import asyncio
import json
import logging
from typing import Any

from app.config import load
from app.redmine import RedmineClient

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    try:
        return asyncio.run(_handle(event))
    except Exception as e:
        logger.exception("予期しないエラー: %s", e)
        return _resp(500, {"error": str(e)})


async def _handle(event: dict[str, Any]) -> dict[str, Any]:
    cfg = load()

    body = _parse_body(event)
    if not body:
        return _resp(400, {"error": "Invalid body"})

    session_id: str = body.get("session_id", "")
    status: str = body.get("status", "")

    # Devin Webhook の metadata にチケットIDを埋め込む想定
    # プロンプト生成時に "redmine_issue_id: 42" を含めておく
    metadata: dict[str, Any] = body.get("metadata", {})
    issue_id: int | None = metadata.get("redmine_issue_id")

    if not issue_id:
        # session_idからissue_idを特定できない場合はログのみ
        logger.warning("redmine_issue_id が metadata にありません: session=%s", session_id)
        return _resp(200, {"message": "no issue_id"})

    redmine = RedmineClient(cfg.redmine_url, cfg.redmine_api_key)

    if status in ("completed", "finished"):
        pr_url: str = body.get("pull_request_url", "")
        comment = (
            f"✅ Devinが作業を完了しました。\n"
            f"Session ID: `{session_id}`\n"
        )
        if pr_url:
            comment += f"PR: {pr_url}"
    else:
        comment = (
            f"⚠️ Devinセッションが終了しました (status: {status})\n"
            f"Session ID: `{session_id}`"
        )

    await redmine.add_comment(issue_id, comment)
    logger.info("Devin完了通知: issue #%s, session %s, status %s", issue_id, session_id, status)
    return _resp(200, {"message": "ok"})


def _parse_body(event: dict[str, Any]) -> dict[str, Any] | None:
    body = event.get("body", "")
    if not body:
        return None
    try:
        return json.loads(body)
    except json.JSONDecodeError:
        return None


def _resp(status: int, body: dict[str, Any]) -> dict[str, Any]:
    return {
        "statusCode": status,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps(body, ensure_ascii=False),
    }
