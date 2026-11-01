"""化学式解析与摩尔质量。

支持的写法：
- 元素与下标：H2O、Fe2O3、C6H12O6
- 括号嵌套：Ca(OH)2、Al2(SO4)3、K4[Fe(CN)6]
- 结晶水：CuSO4·5H2O、Na2CO3·10H2O（也支持 * 和 •）
- 电荷（末尾）：Fe^3+、SO4^2-、NH4^+

不支持的写法会抛 ChemError，并给出 code，方便上层决定怎么解释。
"""

from __future__ import annotations

import json
import re
from dataclasses import dataclass, field
from functools import lru_cache
from pathlib import Path

from .errors import ChemError

_FACTS = Path(__file__).resolve().parent / "facts" / "elements.json"


@lru_cache(maxsize=1)
def elements() -> dict[str, dict]:
    """元素表：symbol -> {name, mass, z}。"""
    data = json.loads(_FACTS.read_text(encoding="utf-8"))
    return data["elements"]


@dataclass
class Composition:
    """一个化学式的组成。"""

    text: str
    counts: dict[str, int] = field(default_factory=dict)
    charge: int = 0

    def molar_mass(self) -> float:
        table = elements()
        total = 0.0
        for symbol, n in self.counts.items():
            total += table[symbol]["mass"] * n
        return total

    def atoms(self) -> int:
        return sum(self.counts.values())

    def __str__(self) -> str:  # pragma: no cover - 展示用
        return self.text


_CHARGE_RE = re.compile(r"\^(\d*)([+-])\s*$")
_HYDRATE_CHARS = "·*•"


def _split_charge(text: str) -> tuple[str, int]:
    m = _CHARGE_RE.search(text)
    if not m:
        return text, 0
    digits = m.group(1) or "1"
    try:
        value = int(digits)
    except ValueError:
        raise ChemError("BAD_CHARGE", f"电荷写法无法识别：{m.group(0)}") from None
    sign = 1 if m.group(2) == "+" else -1
    return text[: m.start()].strip(), value * sign


def _split_hydrate(text: str) -> list[str]:
    parts: list[str] = []
    buf: list[str] = []
    depth = 0
    for ch in text:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch in _HYDRATE_CHARS and depth == 0:
            parts.append("".join(buf))
            buf = []
        else:
            buf.append(ch)
    parts.append("".join(buf))
    return [p.strip() for p in parts if p.strip()]


class _Parser:
    def __init__(self, text: str) -> None:
        self.text = text
        self.pos = 0
        self.n = len(text)

    def error(self, message: str) -> ChemError:
        return ChemError(
            "BAD_FORMULA",
            f"化学式解析失败：{message}",
            hint=f"位置 {self.pos}，原文「{self.text}」",
        )

    def peek(self) -> str:
        return self.text[self.pos] if self.pos < self.n else ""

    def take(self) -> str:
        ch = self.text[self.pos]
        self.pos += 1
        return ch

    def parse_sequence(self, stop: str = "") -> dict[str, int]:
        counts: dict[str, int] = {}
        got = False
        while self.pos < self.n:
            ch = self.peek()
            if stop and ch == stop:
                break
            if ch == "(" or ch == "[":
                close = ")" if ch == "(" else "]"
                self.take()
                inner = self.parse_sequence(close)
                if self.peek() != close:
                    raise self.error(f"括号不匹配，缺少 {close}")
                self.take()
                mult = self.parse_number()
                for symbol, n in inner.items():
                    counts[symbol] = counts.get(symbol, 0) + n * mult
                got = True
                continue
            if ch in ")]":
                if stop:
                    break
                raise self.error(f"多余的右括号 {ch}")
            if ch.isalpha():
                symbol = self.parse_element()
                mult = self.parse_number()
                counts[symbol] = counts.get(symbol, 0) + mult
                got = True
                continue
            if ch.isdigit():
                raise self.error("数字前面缺少元素或括号")
            raise self.error(f"无法识别的字符「{ch}」")
        if not got:
            raise self.error("没有可解析的内容")
        return counts

    def parse_element(self) -> str:
        if not self.peek().isupper():
            raise self.error("元素符号必须以大写字母开头")
        symbol = self.take()
        if self.pos < self.n and self.peek().islower():
            symbol += self.take()
        table = elements()
        if symbol not in table:
            raise ChemError(
                "UNKNOWN_ELEMENT",
                f"元素符号「{symbol}」不在元素表里",
                hint="检查大小写，或确认这是不是某个基团/缩写",
            )
        return symbol

    def parse_number(self) -> int:
        start = self.pos
        while self.pos < self.n and self.peek().isdigit():
            self.pos += 1
        if start == self.pos:
            return 1
        value = int(self.text[start : self.pos])
        if value <= 0:
            raise self.error("下标必须大于 0")
        return value


def parse_formula(text: str) -> Composition:
    """解析化学式，返回 Composition。"""
    raw = (text or "").strip()
    if not raw:
        raise ChemError("EMPTY_FORMULA", "化学式为空")
    body, charge = _split_charge(raw)

    total: dict[str, int] = {}
    for part in _split_hydrate(body):
        multiplier = 1
        m = re.match(r"^(\d+)\s*(.*)$", part)
        if m and m.group(2):
            multiplier = int(m.group(1))
            part = m.group(2)
        parser = _Parser(part)
        counts = parser.parse_sequence()
        if parser.pos != parser.n:
            raise ChemError(
                "BAD_FORMULA",
                f"化学式「{part}」有多余内容",
                hint=f"停在位置 {parser.pos}",
            )
        for symbol, n in counts.items():
            total[symbol] = total.get(symbol, 0) + n * multiplier

    if not total:
        raise ChemError("BAD_FORMULA", f"化学式「{raw}」没有解析出任何元素")
    return Composition(text=raw, counts=total, charge=charge)


def molar_mass(text: str) -> float:
    """摩尔质量，g/mol。"""
    return parse_formula(text).molar_mass()
