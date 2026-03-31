"""環境変数から設定を読み込む。"""

from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class Config:
    devin_api_key: str
    devin_api_base: str
    redmine_url: str
    redmine_api_key: str
    webhook_secret: str | None
    default_template: str
    worker_function_name: str


def load() -> Config:
    return Config(
        devin_api_key=_require("DEVIN_API_KEY"),
        devin_api_base=os.environ.get("DEVIN_API_BASE", "https://api.devin.ai/v1").rstrip("/"),
        redmine_url=_require("REDMINE_URL").rstrip("/"),
        redmine_api_key=_require("REDMINE_API_KEY"),
        webhook_secret=os.environ.get("WEBHOOK_SECRET"),
        default_template=os.environ.get("DEFAULT_TEMPLATE", "default.j2"),
        worker_function_name=os.environ.get("WORKER_FUNCTION_NAME", "redmine-devin-worker"),
    )


def _require(key: str) -> str:
    val = os.environ.get(key)
    if not val:
        raise RuntimeError(f"環境変数 {key} が設定されていません")
    return val
