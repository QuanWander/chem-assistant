"""把核心能力组装成「给模型看的上下文」，供各平台适配器复用。

适配器（AstrBot / MCP / HTTP）只负责：
1. 调 build_context 拿到 notes / cards / 安全提示；
2. 决定怎么注入或渲染；
3. 暴露工具函数。
"""

from __future__ import annotations

from .answer import ChemAnswer, Citation
from .policy import check_safety, grade_from_book, lab_safety_note
from .retrieval import search

CHEM_KEYWORDS = [
    "化学", "方程式", "配平", "离子", "摩尔", "物质的量", "氧化", "还原",
    "溶液", "溶解度", "酸碱", "pH", "元素", "周期表", "实验", "反应",
    "气体", "沉淀", "电解", "原电池", "有机物", "乙醇", "乙酸", "苯",
    "钠", "氯", "铁", "硫", "氮", "碳", "金属", "化合价", "电子",
]


def looks_like_chemistry(text: str) -> bool:
    body = text or ""
    return any(word in body for word in CHEM_KEYWORDS)


def card_to_text(card: dict, *, show_citations: bool = True) -> str:
    lines = [f"【{card.get('title', '')}】{card.get('summary', '')}"]
    points = card.get("key_points") or []
    if points:
        lines.append("要点：")
        lines.extend(f"- {p}" for p in points)
    equations = card.get("equations") or []
    if equations:
        lines.append("相关方程式：")
        lines.extend(f"- {e}" for e in equations)
    mistakes = card.get("common_mistakes") or []
    if mistakes:
        lines.append("易错点：")
        lines.extend(f"- {m}" for m in mistakes)
    if show_citations and card.get("book"):
        lines.append(f"依据：《{card['book']}》{card.get('chapter', '')}")
    return "\n".join(lines)


def strict_rules(level: str, textbook: str, strict: bool = True) -> str:
    grade = level or "高中"
    if not strict:
        return (
            "【化学助教规则（教学引导模式）】\n"
            f"1. 面向{grade}，教材版本：{textbook}。\n"
            "2. 计算类问题建议调用工具核对；如果没调工具，最终答案必须自己再查一遍。\n"
            "3. 引用教材要给到书名和章节，不能伪造页码或原文。\n"
            "4. 可以用提问的方式引导学生自己得出答案；但涉及事实和计算，仍然不能含糊。\n"
            "5. 题目条件不足或前提错误时，先指出来。\n"
            "6. 不给危险化学品的制作、提纯或使用方法；教材里的演示实验可以讲原理、装置和安全注意事项，但要注明「需教师指导/通风橱内进行」。"
        )
    return (
        "【化学助教规则】\n"
        f"1. 面向{grade}，教材版本：{textbook}。\n"
        "2. 涉及配平、摩尔质量、物质的量、浓度等计算的，必须先调用工具，不许心算，也不许编造工具结果。\n"
        "3. 结论要有依据；引用教材要给到书名和章节，不能伪造页码或原文。\n"
        "4. 不确定就明确说「我不确定」并说明缺什么条件；不知道就说不知道，并给出查证路径。\n"
        "5. 题目条件不足、数据矛盾或前提错误时，先指出问题，再谈能不能算。\n"
        "6. 超出当前学段的内容可以拓展，但必须标注「拓展」。\n"
        "7. 不给危险化学品的制作、提纯或使用方法；但教材里的演示实验可以讲原理、装置和安全注意事项，需注明「需教师指导，在通风橱内进行」，不给家庭替代方案。\n"
        "8. 化学用语要规范：下标、↑↓、反应条件、电荷、电子式。"
    )


def build_context(
    question: str,
    *,
    level: str = "高中",
    textbook: str = "人教版",
    max_cards: int = 2,
    show_citations: bool = True,
    strict: bool = True,
) -> dict:
    """返回 {refused, safety_note, rules, cards, hits}。"""
    verdict = check_safety(question)
    if verdict.refused:
        return {
            "refused": True,
            "message": verdict.message,
            "hint": verdict.hint,
            "rules": "",
            "cards": [],
            "safety_note": "",
        }

    hits = search(question, k=max_cards)
    return {
        "refused": False,
        "rules": strict_rules(level, textbook, strict=strict),
        "cards": [card_to_text(c, show_citations=show_citations) for c in hits],
        "hits": hits,
        "safety_note": lab_safety_note(question),
        "phase": "初中" if level == "初三" else "高中",
    }


def make_answer(
    conclusion: str,
    *,
    steps: list[str] | None = None,
    citations: list[Citation] | None = None,
    confidence: str = "medium",
    caveats: list[str] | None = None,
    safety: str = "",
    grade: str = "",
) -> ChemAnswer:
    return ChemAnswer(
        status="ok",
        conclusion=conclusion,
        steps=steps or [],
        citations=citations or [],
        confidence=confidence,
        caveats=caveats or [],
        safety=safety,
        grade=grade,
    )
