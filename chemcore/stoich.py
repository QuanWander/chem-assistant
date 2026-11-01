"""化学计量：物质的量、质量、气体体积、浓度、稀释、产率。

单位约定：
- 质量 g
- 体积 L
- 浓度 mol/L
- 气体体积默认标准状况（0 ℃、101 kPa），摩尔体积 22.4 L/mol（中学教材常用值）
"""

from __future__ import annotations

from .errors import ChemError
from .facts import constant
from .formula import molar_mass as _molar_mass
from .formula import parse_formula


def _positive(value: float, name: str) -> float:
    try:
        v = float(value)
    except (TypeError, ValueError):
        raise ChemError("BAD_NUMBER", f"{name} 不是有效数字：{value!r}") from None
    if v <= 0:
        raise ChemError("NON_POSITIVE", f"{name} 必须大于 0，收到 {v}")
    return v


def molar_mass(formula: str) -> float:
    """摩尔质量 g/mol。"""
    return _molar_mass(formula)


def moles_from_mass(mass_g: float, formula: str) -> float:
    """n = m / M。"""
    m = _positive(mass_g, "质量")
    M = molar_mass(formula)
    return m / M


def mass_from_moles(moles: float, formula: str) -> float:
    """m = n × M。"""
    n = _positive(moles, "物质的量")
    return n * molar_mass(formula)


def gas_volume_stp(moles: float, molar_volume: float | None = None) -> float:
    """V = n × Vm（标准状况，L）。"""
    n = _positive(moles, "物质的量")
    vm = float(molar_volume if molar_volume is not None else (constant("molar_volume_stp") or 22.4))
    if vm <= 0:
        raise ChemError("NON_POSITIVE", "摩尔体积必须大于 0")
    return n * vm


def moles_from_gas_volume_stp(volume_l: float, molar_volume: float | None = None) -> float:
    """n = V / Vm（标准状况）。"""
    v = _positive(volume_l, "气体体积")
    vm = float(molar_volume if molar_volume is not None else (constant("molar_volume_stp") or 22.4))
    if vm <= 0:
        raise ChemError("NON_POSITIVE", "摩尔体积必须大于 0")
    return v / vm


def concentration(moles: float, volume_l: float) -> float:
    """c = n / V，mol/L。"""
    n = _positive(moles, "物质的量")
    v = _positive(volume_l, "溶液体积")
    return n / v


def moles_from_concentration(c: float, volume_l: float) -> float:
    """n = c × V。"""
    c = _positive(c, "浓度")
    v = _positive(volume_l, "溶液体积")
    return c * v


def dilute(
    c1: float | None = None,
    v1: float | None = None,
    c2: float | None = None,
    v2: float | None = None,
) -> dict:
    """稀释计算：c1·V1 = c2·V2，给定任意三个求第四个。

    返回 {"c1":..., "v1":..., "c2":..., "v2":...}。
    """
    known = {"c1": c1, "v1": v1, "c2": c2, "v2": v2}
    if sum(1 for x in known.values() if x is not None) != 3:
        raise ChemError("MISSING_DATA", "稀释计算需要给定三个量，求第四个", hint="c1·V1 = c2·V2")
    for name, value in known.items():
        if value is not None:
            known[name] = _positive(value, {"c1": "稀释前浓度", "v1": "稀释前体积", "c2": "稀释后浓度", "v2": "稀释后体积"}[name])
    if known["v2"] is None:
        known["v2"] = known["c1"] * known["v1"] / known["c2"]
    elif known["v1"] is None:
        known["v1"] = known["c2"] * known["v2"] / known["c1"]
    elif known["c2"] is None:
        known["c2"] = known["c1"] * known["v1"] / known["v2"]
    elif known["c1"] is None:
        known["c1"] = known["c2"] * known["v2"] / known["v1"]
    return known


def percent_yield(actual: float, theoretical: float) -> float:
    """产率 = 实际 / 理论 × 100%。"""
    a = _positive(actual, "实际产量")
    t = _positive(theoretical, "理论产量")
    return a / t * 100.0


def mass_percent(solute_mass: float, solution_mass: float) -> float:
    """溶质质量分数 = 溶质质量 / 溶液质量 × 100%。"""
    s = _positive(solute_mass, "溶质质量")
    total = _positive(solution_mass, "溶液质量")
    if s > total:
        raise ChemError("INVALID_DATA", "溶质质量不能大于溶液质量")
    return s / total * 100.0


def limiting_reagent(amounts: list[tuple[str, float]], equation: str) -> dict:
    """判断限量试剂。

    amounts: [(化学式, 物质的量), ...]
    equation: 已配平的方程式（系数可用）
    返回 {"limiting": 化学式, "amounts": {化学式: 物质的量}, "coefficients": {...}}
    """
    from .equation import balance_equation

    result = balance_equation(equation)
    coeffs = {}
    for sp in result.species:
        if sp.side == "left":
            coeffs[sp.formula] = sp.coefficient

    check = {}
    for formula, n in amounts:
        if formula not in coeffs:
            raise ChemError("NOT_REACTANT", f"{formula} 不在方程式的反应物里")
        check[formula] = _positive(n, f"{formula} 的物质的量") / coeffs[formula]

    if not check:
        raise ChemError("MISSING_DATA", "没有提供反应物的物质的量")
    limiting = min(check, key=check.get)
    return {
        "limiting": limiting,
        "amounts": dict(amounts),
        "coefficients": coeffs,
        "ratio": check,
    }
