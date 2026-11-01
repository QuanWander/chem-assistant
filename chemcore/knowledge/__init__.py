"""人教版教材目录与知识点索引。

v1 只做目录级索引；知识点卡片放在 cards/ 下，按章节 id 关联。
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_BASE = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def catalog() -> dict:
    return json.loads((_BASE / "catalog.json").read_text(encoding="utf-8"))


def all_chapters() -> list[dict]:
    """展开成 [{stage, book, chapter}]，stage 为 junior/senior。"""
    data = catalog()
    rows: list[dict] = []
    for stage in ("junior", "senior"):
        for book, chapters in data.get(stage, {}).items():
            for chapter in chapters:
                rows.append({"stage": stage, "book": book, "chapter": chapter})
    return rows


def find_chapter(keyword: str) -> list[dict]:
    """按关键词找章节（简单的子串匹配，v1 不上向量检索）。"""
    key = (keyword or "").strip()
    if not key:
        return []
    return [row for row in all_chapters() if key in row["chapter"] or key in row["book"]]


def stage_of_book(book: str) -> str | None:
    for stage in ("junior", "senior"):
        if book in catalog().get(stage, {}):
            return stage
    return None
