"""
Unit tests for SkillQuery test cases using unittest/pytest.
"""

import sys
import unittest
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from query_engine import process_query
from sql_guard import validate_sql
from course_taxonomy import resolve_category, resolve_department

class TestSkillQuery(unittest.TestCase):

    def test_taxonomy_resolution(self):
        cat = resolve_category("How many students completed frontend courses?")
        self.assertIsNotNone(cat)
        self.assertEqual(cat["key"], "frontend")

        dept = resolve_department("How many CSE students completed Python?")
        self.assertIsNotNone(dept)
        self.assertEqual(dept["code"], "CS")

    def test_security_rejections(self):
        with self.assertRaises(ValueError):
            validate_sql("DROP TABLE ps_cleared_course_view;")

        with self.assertRaises(ValueError):
            validate_sql("SELECT * FROM ps_cleared_course_view; DELETE FROM ps_cleared_course_view;")

        with self.assertRaises(ValueError):
            validate_sql("SELECT * FROM information_schema.tables;")

    def test_frontend_category_count(self):
        res = process_query("unit_test_session_1", "How many students completed frontend courses?")
        self.assertIn("1,093 students", res["answer"])
        self.assertEqual(res["meta"]["category"], "frontend")

    def test_multi_course_query(self):
        res = process_query("unit_test_session_2", "How many students completed both Python and Java?")
        self.assertIn("1,059 students", res["answer"])

if __name__ == "__main__":
    unittest.main()
