"""HTTP 适配器：给 QQ 桥接、QQAgent、其他语言调用。

零依赖（标准库 http.server），默认监听 127.0.0.1:8765。

接口：
  GET  /health
  POST /v1/ask          {question, level?, textbook?, max_cards?}
  POST /v1/balance      {equation}
  POST /v1/molar_mass   {formula}
  POST /v1/calculate    {kind, formula?, a?, b?}
  POST /v1/safety       {question}
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))))

from chemcore import ChemError, acidbase, balance_equation, parse_formula, stoich
from chemcore.policy import check_safety, lab_safety_note
from chemcore.service import build_context


def _ask(body: dict) -> dict:
    question = str(body.get("question") or "")
    try:
        max_cards = int(body.get("max_cards") or 2)
    except (TypeError, ValueError):
        max_cards = 2
    ctx = build_context(
        question,
        level=str(body.get("level") or "高中"),
        textbook=str(body.get("textbook") or "人教版"),
        max_cards=max_cards,
        show_citations=bool(body.get("show_citations", True)),
    )
    if ctx.get("refused"):
        return {"status": "refused", "message": ctx["message"], "hint": ctx["hint"]}
    return {
        "status": "ok",
        "rules": ctx["rules"],
        "cards": ctx["cards"],
        "hits": [c.get("id") for c in ctx.get("hits", [])],
        "safety": ctx.get("safety_note") or "",
    }


def _balance(body: dict) -> dict:
    try:
        result = balance_equation(str(body.get("equation") or ""))
    except ChemError as exc:
        return {"status": "error", "error": exc.to_dict()}
    return {"status": "ok", "equation": result.formatted(), "checks": result.checks}


def _molar_mass(body: dict) -> dict:
    try:
        comp = parse_formula(str(body.get("formula") or ""))
    except ChemError as exc:
        return {"status": "error", "error": exc.to_dict()}
    return {
        "status": "ok",
        "formula": comp.text,
        "molar_mass": round(comp.molar_mass(), 3),
        "atoms": comp.atoms(),
        "charge": comp.charge,
    }


def _calculate(body: dict) -> dict:
    kind = str(body.get("kind") or "")
    formula = str(body.get("formula") or "")
    try:
        a = float(body.get("a") or 0)
        b = float(body.get("b") or 0)
    except (TypeError, ValueError):
        return {"status": "error", "error": {"code": "BAD_NUMBER", "message": "a/b 必须是数字"}}
    try:
        if kind == "moles_from_mass":
            value = stoich.moles_from_mass(a, formula)
        elif kind == "mass_from_moles":
            value = stoich.mass_from_moles(a, formula)
        elif kind == "gas_volume_stp":
            value = stoich.gas_volume_stp(a)
        elif kind == "moles_from_gas_volume_stp":
            value = stoich.moles_from_gas_volume_stp(a)
        elif kind == "concentration":
            value = stoich.concentration(a, b)
        elif kind == "moles_from_concentration":
            value = stoich.moles_from_concentration(a, b)
        else:
            return {"status": "error", "error": {"code": "BAD_KIND", "message": f"不支持的计算类型：{kind}"}}
    except (ChemError, ValueError) as exc:
        detail = exc.to_dict() if isinstance(exc, ChemError) else {"code": "BAD_NUMBER", "message": str(exc)}
        return {"status": "error", "error": detail}
    return {"status": "ok", "kind": kind, "value": round(value, 6)}


def _ph(body: dict) -> dict:
    kind = str(body.get("kind") or "")
    try:
        c = float(body.get("c") or 0)
        ka = float(body.get("ka") or 0)
        kb = float(body.get("kb") or 0)
    except (TypeError, ValueError):
        return {"status": "error", "error": {"code": "BAD_NUMBER", "message": "c/ka/kb 必须是数字"}}
    try:
        if kind == "strong_acid":
            r = acidbase.ph_strong_acid(c)
        elif kind == "strong_base":
            r = acidbase.ph_strong_base(c)
        elif kind == "weak_acid":
            r = acidbase.ph_weak_acid(c, ka)
        elif kind == "weak_base":
            r = acidbase.ph_weak_base(c, kb)
        else:
            return {"status": "error", "error": {"code": "BAD_KIND", "message": f"不支持的 pH 类型：{kind}"}}
    except ChemError as exc:
        return {"status": "error", "error": exc.to_dict()}
    return {"status": "ok", **r.to_dict()}


def _safety(body: dict) -> dict:
    question = str(body.get("question") or "")
    verdict = check_safety(question)
    return {
        "status": "ok",
        "refused": verdict.refused,
        "category": verdict.category,
        "message": verdict.message,
        "lab_safety": lab_safety_note(question),
    }


ROUTES = {
    "/v1/ask": _ask,
    "/v1/balance": _balance,
    "/v1/molar_mass": _molar_mass,
    "/v1/calculate": _calculate,
    "/v1/safety": _safety,
    "/v1/ph": _ph,
}


class Handler(BaseHTTPRequestHandler):
    def _send(self, payload: dict, code: int = 200) -> None:
        data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_GET(self):  # noqa: N802
        if self.path == "/health":
            self._send({"status": "ok", "service": "chem-assistant"})
        else:
            self._send({"status": "error", "error": {"code": "NOT_FOUND", "message": "见 README 的接口列表"}}, 404)

    def do_POST(self):  # noqa: N802
        handler = ROUTES.get(self.path)
        if handler is None:
            self._send({"status": "error", "error": {"code": "NOT_FOUND", "message": "见 README 的接口列表"}}, 404)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
            body = json.loads(self.rfile.read(length).decode("utf-8") or "{}")
        except (ValueError, UnicodeDecodeError):
            self._send({"status": "error", "error": {"code": "BAD_JSON", "message": "请求体不是合法 JSON"}}, 400)
            return
        try:
            self._send(handler(body))
        except Exception as exc:  # pragma: no cover - 防御
            self._send({"status": "error", "error": {"code": "INTERNAL", "message": str(exc)}}, 500)

    def log_message(self, fmt, *args):  # pragma: no cover
        sys.stderr.write("[chem-http] " + fmt % args + "\n")


def main() -> None:
    parser = argparse.ArgumentParser(description="chem-assistant HTTP adapter")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    args = parser.parse_args()
    server = ThreadingHTTPServer((args.host, args.port), Handler)
    print(f"chem-assistant HTTP listening on http://{args.host}:{args.port}")
    server.serve_forever()


if __name__ == "__main__":
    main()
