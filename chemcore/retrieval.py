"""知识点检索（v1：关键词 + 别名 + 字符重叠，不依赖向量模型）。"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_CARDS_DIR = Path(__file__).resolve().parent / "knowledge" / "cards"


@lru_cache(maxsize=1)
def cards() -> list[dict]:
    rows: list[dict] = []
    if not _CARDS_DIR.exists():
        return rows
    for path in sorted(_CARDS_DIR.glob("*.json")):
        data = json.loads(path.read_text(encoding="utf-8"))
        if isinstance(data, dict):
            data = data.get("cards", [])
        for card in data:
            card.setdefault("source_file", path.name)
            rows.append(card)
    return rows


def _score(card: dict, query: str) -> int:
    text = query or ""
    score = 0
    for alias in card.get("aliases", []):
        alias = str(alias).strip()
        if alias and alias in text:
            score += 3
    title = str(card.get("title", ""))
    if title and title in text:
        score += 4
    for point in card.get("key_points", []):
        for token in _tokens(str(point)):
            if token and token in text:
                score += 1
    for tag in card.get("tags", []):
        if str(tag) in text:
            score += 2
    return score


def _tokens(text: str) -> list[str]:
    """粗粒度切词：中文按 2-4 字片段，英文/数字按词。"""
    tokens: list[str] = []
    for chunk in _split_chunks(text):
        if chunk.isascii():
            tokens.append(chunk)
        elif len(chunk) >= 2:
            for size in (2, 3, 4):
                for i in range(0, len(chunk) - size + 1):
                    tokens.append(chunk[i : i + size])
    return tokens


def _split_chunks(text: str) -> list[str]:
    chunks: list[str] = []
    buf: list[str] = []
    for ch in text:
        if ch.isascii() and (ch.isalnum() or ch in "^+-"):
            buf.append(ch)
        else:
            if buf:
                chunks.append("".join(buf))
                buf = []
            chunks.append(ch)
    if buf:
        chunks.append("".join(buf))
    return [c for c in chunks if c.strip()]


def search(query: str, k: int = 3, stage: str | None = None, book: str | None = None, min_ratio: float = 0.0) -> list[dict]:
    """返回最相关的 k 张卡片（分数为 0 的不返回）。"""
    ranked = []
    for card in cards():
        if stage and card.get("stage") != stage:
            continue
        if book and book not in str(card.get("book", "")):
            continue
        score = _score(card, query)
        if score > 0:
            ranked.append((score, card))
    ranked.sort(key=lambda item: (-item[0], item[1].get("id", "")))
    if ranked and min_ratio > 0:
        best = ranked[0][0]
        ranked = [item for item in ranked if item[0] >= best * min_ratio]
    return [card for _, card in ranked[:k]]
