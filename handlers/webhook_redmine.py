"""Lambda A: Redmine Webhook受信 → @devin検知 → Devinセッション起動。"""

from __future__ import annotations

import asyncio
import hashlib
import hmac
import json
import logging
import re
from typing import Any

from app.config import load
from app.devin import DevinClient
from app.prompt import build_prompt
from app.redmine import RedmineClient

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_MENTION_RE = re.compile(r"@devin\s*(.*)", re.IGNORECASE | re.DOTALL)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    try:
        return asyncio.run(_handle(event))
    except Exception as e:
        logger.exception("予期しないエラー: %s", e)
        return _resp(500, {"error": str(e)})


async def _handle(event: dict[str, Any]) -> dict[str, Any]:
    cfg = load()

    # 署名検証
    if cfg.webhook_secret:
        if not _verify_signature(event, cfg.webhook_secret):
            logger.warning("署名検証失敗")
            return _resp(401, {"error": "Invalid signature"})

    body = _parse_body(event)
    if not body:
        return _resp(400, {"error": "Invalid body"})

    # Redmine Webhook のペイロード構造に対応
    # コメント(journal)のあるイベントのみ処理
    journal = body.get("journal", {})
    notes: str = journal.get("notes", "")

    match = _MENTION_RE.search(notes)
    if not match:
        logger.info("@devin メンションなし、スキップ")
        return _resp(200, {"message": "no mention"})

    mention_text = match.group(1).strip() or "このチケットの内容を確認して対応してください"

    # チケットID取得
    issue_payload = body.get("issue", {})
    issue_id: int | None = issue_payload.get("id")
    if not issue_id:
        return _resp(400, {"error": "issue.id が見つかりません"})

    # Redmineからチケット詳細を取得
    redmine = RedmineClient(cfg.redmine_url, cfg.redmine_api_key)
    issue = await redmine.get_issue(issue_id)

    # プロンプト生成
    prompt = build_prompt(issue, mention_text, cfg.default_template)
    logger.info("プロンプト生成完了 (issue #%s, %d文字)", issue_id, len(prompt))

    # Devinセッション起動
    devin = DevinClient(cfg.devin_api_key, cfg.devin_api_base)
    session = await devin.create_session(prompt)
    session_id: str = session.get("session_id", "unknown")

    # Redmineにコメント
    comment = f"🤖 Devinを起動しました。\nSession ID: `{session_id}`\n作業完了後にこのチケットへ報告します。"
    await redmine.add_comment(issue_id, comment)

    logger.info("Devin起動完了: issue #%s, session %s", issue_id, session_id)
    return _resp(200, {"session_id": session_id})


def _verify_signature(event: dict[str, Any], secret: str) -> bool:
    headers = {k.lower(): v for k, v in (event.get("headers") or {}).items()}
    sig = headers.get("x-redmine-signature", "")
    body_raw = event.get("body", "") or ""
    expected = hmac.new(secret.encode(), body_raw.encode(), hashlib.sha256).hexdigest()
    return hmac.compare_digest(sig, expected)


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
