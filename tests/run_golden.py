"""跑 golden set 的确定性部分。"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chemcore import ChemError, balance_equation, parse_formula
from chemcore.policy import check_safety
from chemcore.retrieval import search

HERE = os.path.dirname(os.path.abspath(__file__))
GOLDEN = json.loads(open(os.path.join(HERE, "golden_set.json"), encoding="utf-8").read())

passed = 0
failed = 0


def check(name: str, ok: bool, detail: str = "") -> None:
    global passed, failed
    if ok:
        passed += 1
        print(f"PASS  {name}")
    else:
        failed += 1
        print(f"FAIL  {name}  {detail}")


def main() -> int:
    for equation, expected in GOLDEN["balance"]:
        try:
            actual = balance_equation(equation).formatted()
        except ChemError as exc:
            check(f"balance: {equation}", False, str(exc))
            continue
        check(f"balance: {equation}", actual == expected, f"got {actual!r}")

    for formula, expected in GOLDEN["molar_mass"]:
        actual = parse_formula(formula).molar_mass()
        check(f"molar: {formula}", abs(actual - expected) < 0.01, f"got {actual}")

    for question in GOLDEN["safety_refuse"]:
        check(f"refuse: {question}", check_safety(question).refused)

    for question in GOLDEN["safety_allow"]:
        check(f"allow: {question}", not check_safety(question).refused)

    for question, card_id in GOLDEN["retrieval"]:
        hits = search(question, k=1)
        actual = hits[0]["id"] if hits else None
        check(f"retrieval: {question}", actual == card_id, f"got {actual}")

    print(f"\nSUMMARY pass={passed} fail={failed}")
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    raise SystemExit(main())
