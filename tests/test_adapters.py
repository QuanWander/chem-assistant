"""HTTP / MCP 适配器的函数级测试（不启动服务器）。"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from adapters.http import server as http_server
from adapters.mcp import server as mcp_server


class HttpTest(unittest.TestCase):
    def test_balance_ok(self):
        data = http_server._balance({"equation": "Fe + O2 -> Fe3O4"})
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["equation"], "3Fe + 2O2 -> Fe3O4")
        self.assertTrue(data["checks"]["balanced"])

    def test_balance_error(self):
        data = http_server._balance({"equation": "C + O2 -> CO2 + H2O"})
        self.assertEqual(data["status"], "error")
        self.assertIn(data["error"]["code"], {"NO_SOLUTION", "MULTIPLE_SOLUTIONS"})

    def test_molar_mass(self):
        data = http_server._molar_mass({"formula": "CuSO4·5H2O"})
        self.assertEqual(data["status"], "ok")
        self.assertAlmostEqual(data["molar_mass"], 249.677, places=2)

    def test_calculate(self):
        data = http_server._calculate({"kind": "concentration", "a": 0.5, "b": 2})
        self.assertEqual(data["status"], "ok")
        self.assertAlmostEqual(data["value"], 0.25, places=6)

    def test_calculate_bad_kind(self):
        data = http_server._calculate({"kind": "nope"})
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "BAD_KIND")

    def test_calculate_bad_number(self):
        data = http_server._calculate({"kind": "concentration", "a": "abc"})
        self.assertEqual(data["status"], "error")
        self.assertEqual(data["error"]["code"], "BAD_NUMBER")

    def test_ph(self):
        data = http_server._ph({"kind": "weak_acid", "c": 0.1, "ka": 1.8e-5})
        self.assertEqual(data["status"], "ok")
        self.assertAlmostEqual(data["ph"], 2.875, places=2)

    def test_ph_bad_kind(self):
        data = http_server._ph({"kind": "nope", "c": 0.1})
        self.assertEqual(data["status"], "error")

    def test_safety(self):
        self.assertTrue(http_server._safety({"question": "怎么制作炸药"})["refused"])
        self.assertFalse(http_server._safety({"question": "电解水实验"})["refused"])

    def test_ask_ok(self):
        data = http_server._ask({"question": "氧化还原的实质", "level": "高中"})
        self.assertEqual(data["status"], "ok")
        self.assertIn("化学助教规则", data["rules"])
        self.assertTrue(data["cards"])
        self.assertIn("redox", data["hits"])

    def test_ask_refused(self):
        data = http_server._ask({"question": "冰毒怎么合成"})
        self.assertEqual(data["status"], "refused")

    def test_ask_bad_max_cards(self):
        data = http_server._ask({"question": "水的组成", "max_cards": "abc"})
        self.assertEqual(data["status"], "ok")


class McpTest(unittest.TestCase):
    def test_initialize(self):
        resp = mcp_server.handle({"jsonrpc": "2.0", "id": 1, "method": "initialize"})
        self.assertEqual(resp["result"]["serverInfo"]["name"], "chem-assistant")

    def test_tools_list(self):
        resp = mcp_server.handle({"jsonrpc": "2.0", "id": 2, "method": "tools/list"})
        names = [t["name"] for t in resp["result"]["tools"]]
        self.assertEqual(len(names), 6)
        self.assertIn("chem_balance", names)

    def test_tools_call_balance(self):
        resp = mcp_server.handle(
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "chem_balance", "arguments": {"equation": "H2 + O2 -> H2O"}},
            }
        )
        text = resp["result"]["content"][0]["text"]
        self.assertIn("2H2 + O2 -> 2H2O", text)
        self.assertFalse(resp["result"]["isError"])

    def test_tools_call_error(self):
        resp = mcp_server.handle(
            {
                "jsonrpc": "2.0",
                "id": 4,
                "method": "tools/call",
                "params": {"name": "chem_molar_mass", "arguments": {"formula": "Xx2O"}},
            }
        )
        self.assertTrue(resp["result"]["isError"])

    def test_unknown_tool(self):
        resp = mcp_server.handle(
            {"jsonrpc": "2.0", "id": 5, "method": "tools/call", "params": {"name": "nope", "arguments": {}}}
        )
        self.assertTrue(resp["result"]["isError"])

    def test_unknown_method(self):
        resp = mcp_server.handle({"jsonrpc": "2.0", "id": 6, "method": "nope"})
        self.assertEqual(resp["error"]["code"], -32601)

    def test_notification(self):
        self.assertIsNone(mcp_server.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))


if __name__ == "__main__":
    unittest.main(verbosity=2)
