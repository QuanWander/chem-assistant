"""命令行适配器。

用法：
    python -m adapters.cli balance "Fe + O2 -> Fe3O4"
    python -m adapters.cli molar "H2SO4"
    python -m adapters.cli calc moles_from_mass --formula H2O --a 18
    python -m adapters.cli ask "氧化还原的实质是什么"
    python -m adapters.cli safety "怎么制作炸药"
"""

from __future__ import annotations

import argparse
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chemcore import ChemError, balance_equation, parse_formula, stoich
from chemcore.policy import check_safety, lab_safety_note
from chemcore.retrieval import search
from chemcore.service import build_context, card_to_text


def main() -> None:
    parser = argparse.ArgumentParser(prog="chem")
    sub = parser.add_subparsers(dest="cmd", required=True)

    p_balance = sub.add_parser("balance")
    p_balance.add_argument("equation")

    p_molar = sub.add_parser("molar")
    p_molar.add_argument("formula")

    p_calc = sub.add_parser("calc")
    p_calc.add_argument("kind")
    p_calc.add_argument("--formula", default="")
    p_calc.add_argument("--a", type=float, default=0)
    p_calc.add_argument("--b", type=float, default=0)

    p_ask = sub.add_parser("ask")
    p_ask.add_argument("question")
    p_ask.add_argument("--level", default="高中")
    p_ask.add_argument("--card", default="")

    p_safety = sub.add_parser("safety")
    p_safety.add_argument("question")

    p_search = sub.add_parser("search")
    p_search.add_argument("question")

    args = parser.parse_args()

    if args.cmd == "balance":
        try:
            result = balance_equation(args.equation)
        except ChemError as exc:
            print(f"配平失败：{exc.message}")
            return
        print(result.formatted())
        print(json.dumps(result.checks, ensure_ascii=False))
    elif args.cmd == "molar":
        try:
            comp = parse_formula(args.formula)
        except ChemError as exc:
            print(f"解析失败：{exc.message}")
            return
        print(f"{comp.text}: {comp.molar_mass():.3f} g/mol")
    elif args.cmd == "calc":
        try:
            value = {
                "moles_from_mass": lambda: stoich.moles_from_mass(args.a, args.formula),
                "mass_from_moles": lambda: stoich.mass_from_moles(args.a, args.formula),
                "gas_volume_stp": lambda: stoich.gas_volume_stp(args.a),
                "moles_from_gas_volume_stp": lambda: stoich.moles_from_gas_volume_stp(args.a),
                "concentration": lambda: stoich.concentration(args.a, args.b),
                "moles_from_concentration": lambda: stoich.moles_from_concentration(args.a, args.b),
            }[args.kind]()
        except KeyError:
            print(f"不支持的计算类型：{args.kind}")
            return
        except ChemError as exc:
            print(f"计算失败：{exc.message}")
            return
        print(f"{value:.6f}")
    elif args.cmd == "search":
        hits = search(args.question, k=3)
        for card in hits:
            print(card_to_text(card))
            print()
    elif args.cmd == "ask":
        ctx = build_context(args.question, level=args.level, max_cards=2)
        if ctx.get("refused"):
            print(ctx["message"])
            print(ctx["hint"])
            return
        print(ctx["rules"])
        print()
        for card in ctx.get("cards", []):
            print(card)
            print()
        if ctx.get("safety_note"):
            print("安全提示：", ctx["safety_note"])
    elif args.cmd == "safety":
        verdict = check_safety(args.question)
        if verdict.refused:
            print(f"必须拒绝：{verdict.message} {verdict.hint}")
        else:
            note = lab_safety_note(args.question)
            print("可以回答。" + (f"实验安全：{note}" if note else ""))


if __name__ == "__main__":
    main()
