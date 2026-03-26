"""Devin API クライアント。"""

from __future__ import annotations

import logging
from typing import Any

import httpx

logger = logging.getLogger(__name__)

_TIMEOUT = httpx.Timeout(30.0, connect=10.0)


class DevinError(Exception):
    def __init__(self, status_code: int, detail: str) -> None:
        self.status_code = status_code
        self.detail = detail
        super().__init__(f"Devin API error {status_code}: {detail}")


class DevinClient:
    def __init__(self, api_key: str, base_url: str) -> None:
        self._base_url = base_url.rstrip("/")
        self._headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def create_session(self, prompt: str) -> dict[str, Any]:
        """セッションを作成して session_id を含むレスポンスを返す。"""
        async with httpx.AsyncClient(base_url=self._base_url, headers=self._headers, timeout=_TIMEOUT) as client:
            resp = await client.post("/sessions", json={"prompt": prompt})
            _raise(resp)
            data: dict[str, Any] = resp.json()
        logger.info("Devin session created: %s", data.get("session_id"))
        return data


def _raise(resp: httpx.Response) -> None:
    if resp.is_success:
        return
    try:
        detail = resp.json().get("detail", resp.text)
    except Exception:
        detail = resp.text
    raise DevinError(resp.status_code, detail)
