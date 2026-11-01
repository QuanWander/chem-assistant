"""酸碱与 pH 计算（25 ℃，稀溶液）。

只做中学范围内、条件明确的计算：
- 强酸/强碱：完全电离；
- 一元弱酸/弱碱：用 Ka/Kb 解一元二次方程，不给近似结果硬套。

缺 Ka/Kb 时会抛错，让上层去问用户，而不是替它假设一个数。
"""

from __future__ import annotations

import math
from dataclasses import dataclass, field

from .errors import ChemError

KW = 1.0e-14


@dataclass
class PhResult:
    ph: float
    h_concentration: float
    oh_concentration: float
    assumptions: list[str] = field(default_factory=list)

    def to_dict(self) -> dict:
        return {
            "ph": round(self.ph, 3),
            "h_concentration": self.h_concentration,
            "oh_concentration": self.oh_concentration,
            "assumptions": list(self.assumptions),
        }


def _positive(value: float, name: str) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ChemError("BAD_NUMBER", f"{name} 不是有效数字：{value!r}") from None
    if v <= 0:
        raise ChemError("NON_POSITIVE", f"{name} 必须大于 0")
    return v


def ph_strong_acid(c: float) -> PhResult:
    """强酸（一元）：[H+] = c。"""
    c = _positive(c, "浓度")
    h = c
    assumptions = ["按强酸完全电离处理"]
    if c < 1e-6:
        assumptions.append("浓度很低，水的电离不可忽略，结果偏大")
    return PhResult(ph=-math.log10(h), h_concentration=h, oh_concentration=KW / h, assumptions=assumptions)


def ph_strong_base(c: float) -> PhResult:
    """强碱（一元）：[OH-] = c。"""
    c = _positive(c, "浓度")
    oh = c
    h = KW / oh
    assumptions = ["按强碱完全电离处理"]
    if c < 1e-6:
        assumptions.append("浓度很低，水的电离不可忽略，结果偏小")
    return PhResult(ph=-math.log10(h), h_concentration=h, oh_concentration=oh, assumptions=assumptions)


def _solve_weak(c: float, k: float) -> float:
    """解 x^2 + k·x − k·c = 0，取正根。"""
    disc = k * k + 4.0 * k * c
    return (-k + math.sqrt(disc)) / 2.0


def ph_weak_acid(c: float, ka: float) -> PhResult:
    """一元弱酸：Ka = x^2 / (c − x)。"""
    c = _positive(c, "浓度")
    ka = _positive(ka, "Ka")
    x = _solve_weak(c, ka)
    assumptions = ["按一元弱酸、只考虑一级电离处理"]
    if x >= c:
        raise ChemError("INVALID_DATA", "弱酸电离度算出来超过 100%，检查浓度或 Ka")
    if c / ka >= 500:
        assumptions.append("c/Ka ≥ 500，可用 [H+]≈√(Ka·c) 近似")
    else:
        assumptions.append("c/Ka < 500，已用一元二次方程精确解，未用近似")
    return PhResult(ph=-math.log10(x), h_concentration=x, oh_concentration=KW / x, assumptions=assumptions)


def ph_weak_base(c: float, kb: float) -> PhResult:
    """一元弱碱：Kb = x^2 / (c − x)，再换算 pH。"""
    c = _positive(c, "浓度")
    kb = _positive(kb, "Kb")
    x = _solve_weak(c, kb)
    assumptions = ["按一元弱碱、只考虑一级电离处理"]
    if x >= c:
        raise ChemError("INVALID_DATA", "弱碱电离度算出来超过 100%，检查浓度或 Kb")
    return PhResult(ph=14.0 - (-math.log10(x)), h_concentration=KW / x, oh_concentration=x, assumptions=assumptions)
