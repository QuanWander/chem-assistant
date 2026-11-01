"""化学方程式配平。

思路：把每个物种的元素计数写成矩阵，反应物为正、生成物为负，
求矩阵的零空间向量，再放大成最小正整数系数。

支持：
- 箭头 -> / → / = / ==
- 物种后的状态符号 (s)(l)(g)(aq)（会被忽略）
- 带电荷的离子：Fe^3+、SO4^2-
- 已有系数（会自动归一化）

不能唯一确定（多个独立解）时会明确报错，而不是猜一个。
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from fractions import Fraction
from math import gcd

from .errors import ChemError
from .formula import Composition, parse_formula

_ARROWS = ("->", "→", "==", "=", "⇒")
_STATE_RE = re.compile(r"\s*\((?:s|l|g|aq)\)\s*$", re.IGNORECASE)
_COEFF_RE = re.compile(r"^\s*(\d+)\s*(.+)$")


@dataclass
class Species:
    text: str
    composition: Composition
    side: str  # "left" / "right"
    coefficient: int = 1

    @property
    def formula(self) -> str:
        return self.composition.text

    @property
    def charge(self) -> int:
        return self.composition.charge


@dataclass
class BalanceResult:
    equation: str
    species: list[Species]
    checks: dict = field(default_factory=dict)

    def formatted(self) -> str:
        left = []
        right = []
        for sp in self.species:
            text = sp.formula
            if sp.coefficient != 1:
                text = f"{sp.coefficient}{text}"
            (left if sp.side == "left" else right).append(text)
        return " + ".join(left) + " -> " + " + ".join(right)


def _split_sides(text: str) -> tuple[str, str]:
    for arrow in _ARROWS:
        if arrow in text:
            left, _, right = text.partition(arrow)
            if left.strip() and right.strip():
                return left, right
    raise ChemError(
        "NO_ARROW",
        "没有找到反应箭头",
        hint="用 -> 或 → 连接反应物和生成物",
    )


def _split_terms(side: str) -> list[str]:
    terms: list[str] = []
    buf: list[str] = []
    depth = 0
    for ch in side:
        if ch in "([":
            depth += 1
        elif ch in ")]":
            depth -= 1
        if ch == "+" and depth == 0:
            # 区分「加号」和「电荷符号」：^+、^2+ 属于电荷，不切分
            tail = "".join(buf).rstrip()
            is_charge = tail.endswith("^") or bool(re.search(r"\^\d+$", tail))
            if not is_charge:
                terms.append("".join(buf))
                buf = []
                continue
        buf.append(ch)
    terms.append("".join(buf))
    return [t.strip() for t in terms if t.strip()]


def _parse_term(term: str, side: str) -> Species:
    raw = term.strip()
    coeff = 1
    m = _COEFF_RE.match(raw)
    if m:
        coeff = int(m.group(1))
        raw = m.group(2).strip()
    body = _STATE_RE.sub("", raw).strip()
    if not body:
        raise ChemError("EMPTY_SPECIES", f"「{term}」不是一个有效的物种")
    comp = parse_formula(body)
    return Species(text=raw, composition=comp, side=side, coefficient=coeff)


def parse_equation(text: str) -> list[Species]:
    left, right = _split_sides(text)
    species = [_parse_term(t, "left") for t in _split_terms(left)]
    species += [_parse_term(t, "right") for t in _split_terms(right)]
    if len(species) < 2:
        raise ChemError("TOO_FEW_SPECIES", "方程式至少要有两个物种")
    return species


def _rref(matrix: list[list[Fraction]]) -> tuple[list[list[Fraction]], list[int]]:
    mat = [row[:] for row in matrix]
    m = len(mat)
    n = len(mat[0]) if m else 0
    pivots: list[int] = []
    r = 0
    for c in range(n):
        pivot = next((i for i in range(r, m) if mat[i][c] != 0), None)
        if pivot is None:
            continue
        mat[r], mat[pivot] = mat[pivot], mat[r]
        pv = mat[r][c]
        mat[r] = [x / pv for x in mat[r]]
        for i in range(m):
            if i != r and mat[i][c] != 0:
                factor = mat[i][c]
                mat[i] = [mat[i][j] - factor * mat[r][j] for j in range(n)]
        pivots.append(c)
        r += 1
        if r == m:
            break
    return mat, pivots


def _nullspace(matrix: list[list[Fraction]]) -> list[list[Fraction]]:
    if not matrix:
        return []
    mat, pivots = _rref(matrix)
    n = len(matrix[0])
    free = [c for c in range(n) if c not in pivots]
    basis: list[list[Fraction]] = []
    for f in free:
        vec = [Fraction(0) for _ in range(n)]
        vec[f] = Fraction(1)
        for row, pc in enumerate(pivots):
            vec[pc] = -mat[row][f]
        basis.append(vec)
    return basis


def _same_sign(vec: list[Fraction]) -> bool:
    positives = sum(1 for x in vec if x > 0)
    negatives = sum(1 for x in vec if x < 0)
    return positives == 0 or negatives == 0


def _to_integers(vec: list[Fraction]) -> list[int]:
    denom_lcm = 1
    for x in vec:
        denom_lcm = denom_lcm * x.denominator // gcd(denom_lcm, x.denominator)
    ints = [int(x * denom_lcm) for x in vec]
    if all(i <= 0 for i in ints):
        ints = [-i for i in ints]
    g = 0
    for i in ints:
        g = gcd(g, abs(i))
    if g == 0:
        raise ChemError("ZERO_SOLUTION", "配平结果是全零")
    return [i // g for i in ints]


def balance_equation(text: str) -> BalanceResult:
    """配平方程式，返回系数与校验结果。"""
    species = parse_equation(text)
    n = len(species)

    symbols: list[str] = []
    for sp in species:
        for symbol in sp.composition.counts:
            if symbol not in symbols:
                symbols.append(symbol)

    rows: list[list[Fraction]] = []
    for symbol in symbols:
        row = []
        for sp in species:
            count = sp.composition.counts.get(symbol, 0)
            row.append(Fraction(count if sp.side == "left" else -count))
        rows.append(row)

    if any(sp.charge for sp in species):
        row = []
        for sp in species:
            q = sp.charge if sp.side == "left" else -sp.charge
            row.append(Fraction(q))
        rows.append(row)

    basis = _nullspace(rows)
    if not basis:
        raise ChemError(
            "NO_SOLUTION",
            "这个方程式无法配平",
            hint="检查化学式是否正确，或反应是否真的能发生",
        )

    candidates = [v for v in basis if _same_sign(v)]
    if not candidates:
        raise ChemError("NO_SOLUTION", "这个方程式没有全正/全负的配平系数")
    if len(candidates) > 1:
        raise ChemError(
            "MULTIPLE_SOLUTIONS",
            "这个方程式有多个独立配平结果，无法唯一确定",
            hint="把反应拆成几个独立的方程式再配",
        )

    coeffs = _to_integers(candidates[0])
    if any(c <= 0 for c in coeffs):
        raise ChemError("NO_SOLUTION", "配平系数出现非正数")
    for sp, c in zip(species, coeffs):
        sp.coefficient = c

    # 校验
    left_counts: dict[str, int] = {}
    right_counts: dict[str, int] = {}
    for sp in species:
        target = left_counts if sp.side == "left" else right_counts
        for symbol, count in sp.composition.counts.items():
            target[symbol] = target.get(symbol, 0) + count * sp.coefficient
    unbalanced = {s: (left_counts.get(s, 0), right_counts.get(s, 0)) for s in symbols if left_counts.get(s, 0) != right_counts.get(s, 0)}

    left_charge = sum(sp.charge * sp.coefficient for sp in species if sp.side == "left")
    right_charge = sum(sp.charge * sp.coefficient for sp in species if sp.side == "right")

    result = BalanceResult(equation=text, species=species)
    result.checks = {
        "balanced": not unbalanced,
        "unbalanced_elements": unbalanced,
        "charge_balanced": left_charge == right_charge,
        "left_charge": left_charge,
        "right_charge": right_charge,
    }
    if unbalanced or left_charge != right_charge:  # pragma: no cover - 理论上不会发生
        raise ChemError("BALANCE_CHECK_FAILED", "配平后校验未通过", hint=str(result.checks))
    return result


def check_ion_equation(text: str) -> BalanceResult:
    """检查离子方程式：既要原子守恒，也要电荷守恒。"""
    result = balance_equation(text)
    if not any(sp.charge for sp in result.species):
        raise ChemError(
            "NOT_IONIC",
            "这个方程式里没有带电荷的离子",
            hint="离子方程式需要用 Fe^3+、SO4^2- 这样的写法",
        )
    return result
