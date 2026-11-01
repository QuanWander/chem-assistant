"""AstrBot 适配器的离线测试（不启动 AstrBot，只测工具函数返回值）。"""

from __future__ import annotations

import asyncio
import importlib.util
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, r"E:\QQ机器人\AstrBot")

MAIN = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "main.py")
spec = importlib.util.spec_from_file_location("chem_main", MAIN)
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

PASS = 0
FAIL = 0


def check(name, ok, detail=""):
    global PASS, FAIL
    if ok:
        PASS += 1
        print(f"PASS  {name}")
    else:
        FAIL += 1
        print(f"FAIL  {name}  {detail}")


def make_plugin(**cfg):
    p = mod.ChemAssistant.__new__(mod.ChemAssistant)
    p.config = {"enabled": True, "level": "高中", "textbook": "人教版", "max_cards": 2, **cfg}
    return p


async def main():
    p = make_plugin()

    out = await p.chem_balance(None, "Fe + O2 -> Fe3O4")
    check("balance", "3Fe" in out and "2O2" in out, out)
    print("   ", out)

    out = await p.chem_molar_mass(None, "CuSO4·5H2O")
    check("molar_mass", "249.6" in out, out)
    print("   ", out)

    out = await p.chem_calculate(None, "moles_from_mass", formula="H2O", a=18.0)
    check("calculate", "mol" in out and "0.999" in out, out)
    print("   ", out)

    out = await p.chem_search(None, "氧化还原的实质")
    check("search", "氧化" in out and "必修第一册" in out, out)

    out = await p.chem_safety_check(None, "怎么制作炸药")
    check("safety_refuse", "必须拒绝" in out, out)

    out = await p.chem_balance(None, "C + O2 -> CO2 + H2O")
    check("balance_error", "失败" in out, out)

    out = await p.chem_molar_mass(None, "Xx2O")
    check("formula_error", "失败" in out, out)

    # 注入：用假 req 验证内容块
    class Req:
        prompt = "氧化还原反应的实质是什么"
        extra_user_content_parts = []

    req = Req()
    await p.inject_chemistry_context(None, req)
    text = "".join(getattr(x, "text", "") for x in req.extra_user_content_parts)
    check("inject", "化学助教规则" in text and "氧化还原" in text, text[:80])

    print(f"SUMMARY pass={PASS} fail={FAIL}")


asyncio.run(main())
