# -*- coding: utf-8 -*-
"""只聊学习模式：按群号 / QQ 号白名单限制话题。"""

from __future__ import annotations

import re

from .service import looks_like_chemistry

# 只放明确指向学习/题目的词，避免把普通聊天误判成学习
_STUDY_HINTS = (
    "作业",
    "考试",
    "测验",
    "周测",
    "月考",
    "期中",
    "期末",
    "卷子",
    "试卷",
    "题目",
    "这道题",
    "做题",
    "刷题",
    "错题",
    "答案",
    "解析",
    "知识点",
    "考点",
    "公式",
    "方程式",
    "化学式",
    "计算",
    "怎么算",
    "怎么做",
    "原理",
    "实验",
    "复习",
    "预习",
    "笔记",
    "上课",
    "课堂",
    "学习",
    "教材",
    "课本",
    "章节",
    "元素",
    "物质",
    "反应",
    "摩尔",
    "浓度",
    "溶液",
    "酸碱",
    "氧化",
    "还原",
)


def parse_ids(value) -> set[str]:
    """兼容 list / 逗号分隔字符串 / 换行分隔字符串。"""
    if value is None:
        return set()
    if isinstance(value, (list, tuple, set)):
        return {str(x).strip() for x in value if str(x).strip()}
    return {x.strip() for x in re.split(r"[,，\s]+", str(value)) if x.strip()}


def is_study_related(text: str) -> bool:
    body = str(text or "").strip()
    if not body:
        return False
    if looks_like_chemistry(body):
        return True
    return any(word in body for word in _STUDY_HINTS)


def should_guard(config: dict, group_id: str | int | None, user_id: str | int | None) -> bool:
    if not bool((config or {}).get("study_only_enabled", False)):
        return False
    groups = parse_ids((config or {}).get("study_only_groups"))
    users = parse_ids((config or {}).get("study_only_users"))
    if not groups and not users:
        return False
    return str(group_id or "") in groups or str(user_id or "") in users
