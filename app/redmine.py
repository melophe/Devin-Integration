"""Redmine API クライアント。"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class RedmineError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Redmine API error {status_code}: {detail}")


class RedmineClient:
    def __init__(self, base_url: str, api_key: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "X-Redmine-API-Key": api_key,
            "Content-Type": "application/json",
        }

    async def get_issue(self, issue_id: int) -> dict[str, Any]:
        """チケット詳細を取得する。"""
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers, timeout=_TIMEOUT) as client:
            resp = await client.get(f"/issues/{issue_id}.json")
            _raise(resp)
            data: dict[str, Any] = resp.json()
        return data.get("issue", data)

    async def add_comment(self, issue_id: int, comment: str) -> None:
        """チケットにコメントを追加する。"""
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers, timeout=_TIMEOUT) as client:
            resp = await client.put(f"/issues/{issue_id}.json", json={"issue": {"notes": comment}})
            _raise(resp)
        logger.info("Redmine issue #%s にコメント追加", issue_id)


def _raise(resp: httpx.Response) -> None:
    if resp.is_success:
        return
    try:
        errors = resp.json().get("errors", [])
        detail = "; ".join(errors) if errors else resp.text
    except Exception:
        detail = resp.text
    raise RedmineError(resp.status_code, detail)
