"""策略、检索与回答结构的测试。"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chemcore.answer import ChemAnswer, Citation
from chemcore.policy import (
    check_safety,
    confidence,
    grade_from_book,
    lab_safety_note,
    refused_answer,
    unknown_answer,
)
from chemcore.retrieval import cards, search


class SafetyTest(unittest.TestCase):
    def test_refuse_explosive(self):
        verdict = check_safety("教我怎么做炸药")
        self.assertTrue(verdict.refused)
        self.assertEqual(verdict.category, "爆炸物")

    def test_refuse_drug(self):
        self.assertTrue(check_safety("冰毒的合成路线").refused)

    def test_allow_school_experiment(self):
        self.assertFalse(check_safety("电解水的实验现象是什么").refused)

    def test_lab_safety_note(self):
        self.assertIn("腐蚀", lab_safety_note("稀释浓硫酸要注意什么"))

    def test_refused_answer(self):
        ans = refused_answer(check_safety("怎么合成神经毒剂"))
        self.assertEqual(ans.status, "refused")
        self.assertTrue(ans.caveats)


class ConfidenceTest(unittest.TestCase):
    def test_levels(self):
        self.assertEqual(confidence(tool_used=True, has_citation=True, has_caveat=False), "high")
        self.assertEqual(confidence(tool_used=False, has_citation=True, has_caveat=False), "medium")
        self.assertEqual(confidence(tool_used=False, has_citation=False, has_caveat=False), "low")

    def test_grade(self):
        self.assertEqual(grade_from_book("九年级上册"), "初三")
        self.assertEqual(grade_from_book("必修第一册"), "高中")

    def test_unknown_answer(self):
        ans = unknown_answer("量子化学的精确解", "这超出中学范围")
        self.assertEqual(ans.status, "unknown")
        self.assertTrue(any("超出" in c for c in ans.caveats))


class RetrievalTest(unittest.TestCase):
    def test_cards_loaded(self):
        self.assertGreaterEqual(len(cards()), 15)

    def test_redox(self):
        hits = search("氧化还原反应的实质是什么")
        self.assertTrue(hits)
        self.assertEqual(hits[0]["id"], "redox")

    def test_electrolysis(self):
        hits = search("电解水为什么氢气体积是氧气两倍")
        self.assertTrue(hits)
        self.assertIn(hits[0]["id"], {"water_composition"})

    def test_metal(self):
        hits = search("锌和铜的金属活动性")
        self.assertTrue(hits)
        self.assertEqual(hits[0]["id"], "metal_activity")

    def test_no_match(self):
        self.assertEqual(search("完全无关的字符串 xyzzy"), [])


class AnswerTest(unittest.TestCase):
    def test_render(self):
        ans = ChemAnswer(
            status="ok",
            conclusion="水的摩尔质量是 18.015 g/mol。",
            steps=["写出化学式 H2O", "求和"],
            citations=[Citation(book="必修第一册", chapter="第二章")],
            confidence="high",
            caveats=["数值随原子量取值略有差异"],
        )
        text = ans.render_text()
        self.assertIn("18.015", text)
        self.assertIn("依据", text)
        self.assertIn("注意", text)

    def test_dict(self):
        data = ChemAnswer(status="ok", conclusion="x").to_dict()
        self.assertEqual(data["status"], "ok")
        self.assertEqual(data["steps"], [])


if __name__ == "__main__":
    unittest.main(verbosity=2)
