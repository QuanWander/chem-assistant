"""结构化回答。各平台适配器都应先拿到这个结构，再决定怎么渲染。"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class Citation:
    book: str
    chapter: str
    detail: str = ""

    def to_dict(self) -> dict:
        data = {"book": self.book, "chapter": self.chapter}
        if self.detail:
            data["detail"] = self.detail
        return data


@dataclass
class ChemAnswer:
    """一个回答的完整结构。

    status:
      - ok: 可以答
      - uncertain: 有依据但存在不确定性，caveats 里写清楚
      - unknown: 不知道，给出查证路径
      - refused: 安全问题拒答
    confidence: high / medium / low
    """

    status: str
    conclusion: str
    steps: list[str] = field(default_factory=list)
    citations: list[Citation] = field(default_factory=list)
    confidence: str = "medium"
    caveats: list[str] = field(default_factory=list)
    safety: str = ""
    grade: str = ""

    def to_dict(self) -> dict:
        return {
            "status": self.status,
            "conclusion": self.conclusion,
            "steps": list(self.steps),
            "citations": [c.to_dict() for c in self.citations],
            "confidence": self.confidence,
            "caveats": list(self.caveats),
            "safety": self.safety,
            "grade": self.grade,
        }

    def render_text(self) -> str:
        lines = [self.conclusion]
        if self.steps:
            lines.append("")
            for i, step in enumerate(self.steps, 1):
                lines.append(f"{i}. {step}")
        if self.caveats:
            lines.append("")
            lines.append("注意：")
            for caveat in self.caveats:
                lines.append(f"- {caveat}")
        if self.citations:
            cites = "；".join(f"《{c.book}》{c.chapter}" for c in self.citations)
            lines.append(f"\n依据：{cites}")
        if self.safety:
            lines.append(f"\n安全提示：{self.safety}")
        return "\n".join(lines)
