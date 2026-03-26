"""Jinja2テンプレートからDevinへのプロンプトを生成する。"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from jinja2 import Environment, FileSystemLoader, StrictUndefined

_TEMPLATES_DIR = Path(__file__).parent.parent / "templates"


def build_prompt(issue: dict[str, Any], mention_text: str, template_name: str = "default.j2") -> str:
    """
    チケット情報とコメントのメンション文からプロンプトを生成する。

    mention_text: @devin 以降のユーザー指示文
    """
    env = Environment(
        loader=FileSystemLoader(str(_TEMPLATES_DIR)),
        undefined=StrictUndefined,
        trim_blocks=True,
        lstrip_blocks=True,
    )
    template = env.get_template(template_name)

    context: dict[str, Any] = {
        "issue": issue,
        "id": issue.get("id"),
        "subject": issue.get("subject", ""),
        "description": issue.get("description", ""),
        "tracker": issue.get("tracker", {}).get("name", ""),
        "status": issue.get("status", {}).get("name", ""),
        "project": issue.get("project", {}).get("name", ""),
        "mention_text": mention_text.strip(),
    }
    return template.render(**context)
