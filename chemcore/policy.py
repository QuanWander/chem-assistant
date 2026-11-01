"""严谨策略：安全拦截、依据分级、不确定三分法。

这里是「不许含糊」的落点：
- 涉及危险操作 → refused，只讲原理和安全，不给可执行步骤；
- 缺条件/数据矛盾 → uncertain，列出 caveats；
- 没有依据 → unknown，给查证路径，不编。
"""

from __future__ import annotations

import re
from dataclasses import dataclass

from .answer import ChemAnswer, Citation

# 直接拒答的方向：攻击性/管制/毒品。命中后只给安全说明，不展开工艺。
_DANGEROUS = [
    (r"炸药|爆炸物|雷管|引爆|起爆药|黑火药|硝化甘油|TNT|三硝基甲苯", "爆炸物"),
    (r"冰毒|甲基苯丙胺|海洛因|可卡因|芬太尼|制毒|毒品合成", "毒品"),
    (r"神经毒剂|沙林|VX|芥子气|化学武器|光气", "化学武器"),
    (r"武器|武器化|投毒|毒害", "投毒/武器化"),
]

# 中学实验里允许讲、但必须带安全提示的操作
_LAB_SAFETY = [
    (r"浓硫酸|浓硝酸|浓盐酸|氢氧化钠|强酸|强碱", "强酸强碱有腐蚀性，必须戴护目镜和手套，在通风处操作，稀释浓硫酸时把酸沿器壁慢慢倒入水中并搅拌。"),
    (r"加热|酒精灯|灼烧", "加热时用试管夹，管口不要对着人，先预热再集中加热。"),
    (r"氯气|二氧化硫|氨气|硫化氢|一氧化碳", "有毒/刺激性气体必须在通风橱中操作，尾气要处理。"),
    (r"钾|钠|锂|白磷|金属钠", "活泼金属/白磷遇水或空气可能燃烧爆炸，按教材要求保存和使用。"),
]


@dataclass
class SafetyVerdict:
    refused: bool
    category: str = ""
    message: str = ""
    hint: str = ""


def check_safety(question: str) -> SafetyVerdict:
    text = question or ""
    for pattern, category in _DANGEROUS:
        if re.search(pattern, text, re.IGNORECASE):
            return SafetyVerdict(
                refused=True,
                category=category,
                message=f"这个问题涉及{category}，我不能提供制作、提纯或使用的具体方法。",
                hint="如果是课程学习，可以问它的化学原理、危害与防护，或者历史上的相关案例。",
            )
    return SafetyVerdict(refused=False)


def lab_safety_note(question: str) -> str:
    text = question or ""
    for pattern, note in _LAB_SAFETY:
        if re.search(pattern, text):
            return note
    return ""


def grade_from_book(book: str) -> str:
    if book.startswith("九年级"):
        return "初三"
    if book.startswith("必修") or book.startswith("选择性必修"):
        return "高中"
    return ""


def confidence(tool_used: bool, has_citation: bool, has_caveat: bool) -> str:
    if tool_used and has_citation and not has_caveat:
        return "high"
    if has_citation or tool_used:
        return "medium"
    return "low"


def unknown_answer(question: str, missing: str = "") -> ChemAnswer:
    caveat = missing or "这个问题超出了我能可靠回答的范围"
    return ChemAnswer(
        status="unknown",
        conclusion="这个我不确定，不能给你一个编出来的答案。",
        caveats=[caveat, "建议查教材对应章节或问老师；如果你告诉我学段和教材版本，我可以帮你定位到章节。"],
        confidence="low",
    )


def refused_answer(verdict: SafetyVerdict) -> ChemAnswer:
    return ChemAnswer(
        status="refused",
        conclusion=verdict.message,
        caveats=[verdict.hint] if verdict.hint else [],
        confidence="high",
        safety="涉及危险化学品时，请以实验室安全规范和专业教师指导为准。",
    )
