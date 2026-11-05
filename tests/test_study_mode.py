# -*- coding: utf-8 -*-
"""只聊学习模式的测试。"""

from __future__ import annotations

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chemcore.study_mode import is_study_related, parse_ids, should_guard


class StudyModeTest(unittest.TestCase):
    def test_parse_ids(self):
        self.assertEqual(parse_ids("123, 456\n789"), {"123", "456", "789"})
        self.assertEqual(parse_ids(["1", "2", " "]), {"1", "2"})
        self.assertEqual(parse_ids(None), set())

    def test_study_related(self):
        self.assertTrue(is_study_related("这道题怎么算"))
        self.assertTrue(is_study_related("氧化还原的实质"))
        self.assertTrue(is_study_related("老师布置的作业"))
        self.assertFalse(is_study_related("今晚打不打塔科夫"))
        self.assertFalse(is_study_related("我好累"))

    def test_guard_group(self):
        cfg = {"study_only_enabled": True, "study_only_groups": ["123"], "study_only_users": []}
        self.assertTrue(should_guard(cfg, "123", "999"))
        self.assertFalse(should_guard(cfg, "456", "999"))

    def test_guard_user(self):
        cfg = {"study_only_enabled": True, "study_only_groups": [], "study_only_users": ["1001"]}
        self.assertTrue(should_guard(cfg, "123", "1001"))
        self.assertFalse(should_guard(cfg, "123", "1002"))

    def test_disabled_or_empty(self):
        self.assertFalse(should_guard({"study_only_enabled": False}, "123", "1"))
        self.assertFalse(should_guard({"study_only_enabled": True}, "123", "1"))


if __name__ == "__main__":
    unittest.main(verbosity=2)
