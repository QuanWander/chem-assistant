"""事实表加载。"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path

_BASE = Path(__file__).resolve().parent


@lru_cache(maxsize=1)
def rules() -> dict:
    return json.loads((_BASE / "rules.json").read_text(encoding="utf-8"))


@lru_cache(maxsize=1)
def elements() -> dict[str, dict]:
    data = json.loads((_BASE / "elements.json").read_text(encoding="utf-8"))
    return data["elements"]


def activity_order() -> list[str]:
    return list(rules()["activity_series"]["order"])


def ion_color(ion: str) -> str | None:
    return rules()["ion_colors"].get(ion)


def gas_test(gas: str) -> dict | None:
    return rules()["gas_tests"].get(gas)


def constant(name: str):
    return rules()["constants"].get(name)


def solubility_rules() -> list[str]:
    return list(rules()["solubility"]["rules"])
