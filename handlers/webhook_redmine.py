"""Lambda A: Redmine Webhook受信 → @devin検知 → Workerを非同期起動して即200返す。"""

from __future__ import annotations

import hashlib
import hmac
import json
import logging
import re
from typing import Any

import boto3

from app.config import load

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)

_MENTION_RE = re.compile(r"@devin\s*(.*)", re.IGNORECASE | re.DOTALL)


def handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    cfg = load()

    # 署名検証
    if cfg.webhook_secret:
        if not _verify_signature(event, cfg.webhook_secret):
            logger.warning("署名検証失敗")
            return _resp(401, {"error": "Invalid signature"})

    body = _parse_body(event)
    if not body:
        return _resp(400, {"error": "Invalid body"})

    journal = body.get("journal", {})
    notes: str = journal.get("notes", "")

    match = _MENTION_RE.search(notes)
    if not match:
        logger.info("@devin メンションなし、スキップ")
        return _resp(200, {"message": "no mention"})

    mention_text = match.group(1).strip() or "このチケットの内容を確認して対応してください"

    issue_id: int | None = body.get("issue", {}).get("id")
    if not issue_id:
        return _resp(400, {"error": "issue.id が見つかりません"})

    # Workerを非同期で起動（レスポンスを待たない）
    payload = json.dumps({"issue_id": issue_id, "mention_text": mention_text})
    boto3.client("lambda").invoke(
        FunctionName=cfg.worker_function_name,
        InvocationType="Event",
        Payload=payload,
    )

    logger.info("Worker起動: issue #%s", issue_id)
    return _resp(200, {"message": "accepted", "issue_id": issue_id})


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
