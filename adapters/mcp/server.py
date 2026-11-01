"""MCP 适配器（stdio）：给 DSH、Claude 等支持 MCP 的 agent 直接调用。

启动：
    python -m adapters.mcp.server
协议：JSON-RPC 2.0，按行分隔（MCP stdio 传输）。
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from chemcore import ChemError, balance_equation, parse_formula, stoich
from chemcore.policy import check_safety, lab_safety_note
from chemcore.retrieval import search
from chemcore.service import build_context, card_to_text

SERVER_INFO = {"name": "chem-assistant", "version": "0.1.0"}
PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {
        "name": "chem_search",
        "description": "检索人教版化学知识卡片（概念、要点、方程式、易错点）。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "question": {"type": "string", "description": "化学问题或关键词"},
                "level": {"type": "string", "description": "初三 / 高中"},
                "max_cards": {"type": "integer", "default": 3},
            },
            "required": ["question"],
        },
    },
    {
        "name": "chem_balance",
        "description": "配平化学方程式，校验原子/电荷守恒。",
        "inputSchema": {
            "type": "object",
            "properties": {"equation": {"type": "string", "description": "用 -> 连接的方程式"}},
            "required": ["equation"],
        },
    },
    {
        "name": "chem_molar_mass",
        "description": "计算化学式的摩尔质量（支持括号、结晶水、电荷）。",
        "inputSchema": {
            "type": "object",
            "properties": {"formula": {"type": "string"}},
            "required": ["formula"],
        },
    },
    {
        "name": "chem_calculate",
        "description": "化学计量计算：moles_from_mass / mass_from_moles / gas_volume_stp / moles_from_gas_volume_stp / concentration / moles_from_concentration。",
        "inputSchema": {
            "type": "object",
            "properties": {
                "kind": {"type": "string"},
                "formula": {"type": "string"},
                "a": {"type": "number"},
                "b": {"type": "number"},
            },
            "required": ["kind"],
        },
    },
    {
        "name": "chem_safety_check",
        "description": "判断问题是否涉及危险化学品操作，返回是否拒答与实验安全提示。",
        "inputSchema": {
            "type": "object",
            "properties": {"question": {"type": "string"}},
            "required": ["question"],
        },
    },
]


def _text_result(text: str, is_error: bool = False) -> dict:
    return {"content": [{"type": "text", "text": text}], "isError": is_error}


def call_tool(name: str, args: dict) -> dict:
    try:
        if name == "chem_search":
            hits = search(str(args.get("question") or ""), k=int(args.get("max_cards") or 3))
            if not hits:
                return _text_result("没有匹配的知识卡；不要编造章节，明确说明依据不足。")
            return _text_result("\n\n".join(card_to_text(c) for c in hits))
        if name == "chem_balance":
            result = balance_equation(str(args.get("equation") or ""))
            return _text_result(f"{result.formatted()}\n校验：{json.dumps(result.checks, ensure_ascii=False)}")
        if name == "chem_molar_mass":
            comp = parse_formula(str(args.get("formula") or ""))
            return _text_result(f"{comp.text} 的摩尔质量 = {comp.molar_mass():.3f} g/mol")
        if name == "chem_calculate":
            kind = str(args.get("kind") or "")
            formula = str(args.get("formula") or "")
            a = float(args.get("a") or 0)
            b = float(args.get("b") or 0)
            table = {
                "moles_from_mass": lambda: stoich.moles_from_mass(a, formula),
                "mass_from_moles": lambda: stoich.mass_from_moles(a, formula),
                "gas_volume_stp": lambda: stoich.gas_volume_stp(a),
                "moles_from_gas_volume_stp": lambda: stoich.moles_from_gas_volume_stp(a),
                "concentration": lambda: stoich.concentration(a, b),
                "moles_from_concentration": lambda: stoich.moles_from_concentration(a, b),
            }
            if kind not in table:
                return _text_result(f"不支持的计算类型：{kind}", is_error=True)
            return _text_result(f"{kind} = {table[kind]():.6f}")
        if name == "chem_safety_check":
            question = str(args.get("question") or "")
            verdict = check_safety(question)
            if verdict.refused:
                return _text_result(f"必须拒绝：{verdict.message} {verdict.hint}")
            note = lab_safety_note(question)
            return _text_result(f"可以回答。{('实验安全：' + note) if note else '未识别到特别危险的实验操作。'}")
        return _text_result(f"未知工具：{name}", is_error=True)
    except ChemError as exc:
        return _text_result(f"计算失败：{exc.message} {exc.hint}", is_error=True)
    except (TypeError, ValueError) as exc:
        return _text_result(f"参数错误：{exc}", is_error=True)


def handle(request: dict) -> dict | None:
    method = request.get("method")
    rid = request.get("id")
    if method == "initialize":
        return {
            "jsonrpc": "2.0",
            "id": rid,
            "result": {
                "protocolVersion": PROTOCOL_VERSION,
                "capabilities": {"tools": {}},
                "serverInfo": SERVER_INFO,
            },
        }
    if method == "notifications/initialized":
        return None
    if method == "ping":
        return {"jsonrpc": "2.0", "id": rid, "result": {}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": rid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        params = request.get("params") or {}
        result = call_tool(str(params.get("name") or ""), params.get("arguments") or {})
        return {"jsonrpc": "2.0", "id": rid, "result": result}
    return {
        "jsonrpc": "2.0",
        "id": rid,
        "error": {"code": -32601, "message": f"Method not found: {method}"},
    }


def main() -> None:
    for line in sys.stdin:
        line = line.strip().lstrip("\ufeff")
        if not line:
            continue
        try:
            request = json.loads(line)
        except json.JSONDecodeError:
            continue
        response = handle(request)
        if response is not None:
            sys.stdout.write(json.dumps(response, ensure_ascii=False) + "\n")
            sys.stdout.flush()


if __name__ == "__main__":
    main()
