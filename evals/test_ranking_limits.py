"""
Regression test suite for SkillQuery Top-N Ranking and Result Limits.
Verifies:
1. Natural language Top-N extraction (Top 5, Top 10, Top 25, Top 50, Top 100, default 10).
2. Safe bounds and maximum limits.
3. Stable tie-breaking and deduplication.
4. Total matching students vs displayed limit accuracy.
5. Live C Programming Level 2 ranking behavior.
"""

import os
import sys
import unittest
from typing import Dict, Any

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from query_engine import (
    process_query,
    extract_rank_limit,
    detect_output_format,
    build_single_or_multi_course_sql,
    build_category_sql
)


class TestRankingLimits(unittest.TestCase):

    def test_extract_rank_limit_explicit_values(self):
        """Verifies natural language extraction across diverse phrasing and numbers."""
        cases = [
            ("Top 5 C students", 5),
            ("Top 10 Java students", 10),
            ("Top 25 Python students", 25),
            ("Top 50 students who cleared C Level 2", 50),
            ("Top 100 frontend students", 100),
            ("First 20 students in cse", 20),
            ("Rank the best 15 students in react", 15),
            ("Show top students in Java", 10),  # default
            ("Who are the top performers in DSA?", 10),  # default
        ]
        for query, expected_limit in cases:
            with self.subTest(query=query):
                limit = extract_rank_limit(query, default=10)
                self.assertEqual(limit, expected_limit, f"Failed for '{query}': expected {expected_limit}, got {limit}")

    def test_extract_rank_limit_ceiling(self):
        """Verifies limit is safely capped at 2000."""
        limit = extract_rank_limit("Top 5000 students in python", default=10, max_limit=2000)
        self.assertEqual(limit, 2000)

    def test_detect_output_format_ranking(self):
        """Verifies RANK intent is recognized for explicit and default top queries."""
        cases = [
            "Top 50 students who has cleared C Level 2",
            "Top 5 C students",
            "Top 10 Java students",
            "Top students in frontend",
            "Rank students in Database",
            "Best students in DSA"
        ]
        for query in cases:
            with self.subTest(query=query):
                fmt = detect_output_format(query)
                self.assertEqual(fmt, "RANK", f"Failed for '{query}': expected RANK, got {fmt}")

    def test_c_level_2_top_50_pipeline(self):
        """Verifies the exact user query: 'Top 50 students who has cleared C Level 2'."""
        query = "Top 50 students who has cleared C Level 2"
        res = process_query("test_session_c_lvl_2", query)

        rows = res["rows"]
        meta = res["meta"]
        answer = res["answer"]

        # 1. Returned rows must match requested limit (or total matches if fewer)
        self.assertEqual(len(rows), 50, f"Expected 50 displayed rows, got {len(rows)}")

        # 2. Total matching students must be > 50 (live DB has 1000+ students for C Level 2)
        total_matching = meta.get("total_matching_students", 0)
        self.assertGreater(total_matching, 50, f"Expected total matching > 50, got {total_matching}")

        # 3. Each student record must be distinct (deduplication)
        roll_numbers = [r["roll_number"] for r in rows]
        self.assertEqual(len(roll_numbers), len(set(roll_numbers)), "Roll numbers must be deduplicated")

        # 4. Deterministic tie-breaking: within equal completed_levels, order must be roll_number ASC
        from itertools import groupby
        for level_val, group in groupby(rows, key=lambda r: int(r["completed_levels"])):
            group_rolls = [r["roll_number"] for r in group]
            self.assertEqual(
                group_rolls,
                sorted(group_rolls),
                f"Tie-breaking failed for completed_levels={level_val}: expected roll_number ASC"
            )

        # 5. Answer must clearly communicate top 50 of total matching students
        self.assertIn("top 50 of", answer.lower(), f"Answer should state 'top 50 of', got: {answer}")
        self.assertNotIn("showing all 10", answer.lower(), "Answer must never say 'showing all 10'")
        self.assertNotIn("showing top 10", answer.lower(), "Answer must never say 'showing top 10'")

    def test_ranking_top_5_database(self):
        """Verifies Top 5 query returns exactly 5 rows."""
        query = "Top 5 students in database programming"
        res = process_query("test_session_db_5", query)
        self.assertEqual(len(res["rows"]), 5, f"Expected 5 rows, got {len(res['rows'])}")
        self.assertIn("top 5 of", res["answer"].lower())

    def test_ranking_top_10_java(self):
        """Verifies Top 10 query returns exactly 10 rows."""
        query = "Top 10 Java students"
        res = process_query("test_session_java_10", query)
        self.assertEqual(len(res["rows"]), 10, f"Expected 10 rows, got {len(res['rows'])}")
        self.assertIn("top 10 of", res["answer"].lower())

    def test_ranking_fewer_than_limit(self):
        """Verifies that if fewer records exist than requested limit, phrasing reflects all qualifying."""
        # Backend has 0 completions, so top 50 backend returns 0 records
        query = "Top 50 students in backend development"
        res = process_query("test_session_backend_50", query)
        self.assertEqual(len(res["rows"]), 0)
        self.assertIn("No matching student records found", res["answer"])


if __name__ == "__main__":
    unittest.main()
