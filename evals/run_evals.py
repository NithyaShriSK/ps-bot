"""
SkillQuery Automated Evaluation Suite Runner.
Executes test_dataset.json against the SkillQuery pipeline, checks metrics,
and outputs a comprehensive benchmark report.
"""

import os
import sys
import json
import time
from pathlib import Path

# Add project root to sys.path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from query_engine import process_query
from session_memory import session_manager
from sql_guard import validate_sql
from evals.metrics import EvalMetrics

def run_evaluation(dataset_path: str = None) -> dict:
    if not dataset_path:
        dataset_path = str(Path(__file__).parent / "test_dataset.json")

    with open(dataset_path, "r", encoding="utf-8") as f:
        tests = json.load(f)

    print(f"==================================================")
    print(f"Starting SkillQuery AI Evaluation: {len(tests)} Test Cases")
    print(f"==================================================")

    metrics = EvalMetrics()
    eval_session_prefix = f"eval_session_{int(time.time())}"

    for idx, tc in enumerate(tests, 1):
        tc_id = tc["id"]
        tc_cat = tc["category"]
        question = tc["question"]
        follow_up = tc.get("follow_up")
        session_id = f"{eval_session_prefix}_{tc_id}"

        print(f"[{idx:02d}/{len(tests):02d}] {tc_id} ({tc_cat}): {question[:45]}...", end=" ")

        # 1. Security Test Handling
        if tc_cat == "security_test":
            try:
                # Test whether sql_guard rejects unsafe SQL query
                validate_sql(question)
                print("FAIL (Security breach: query allowed!)")
                metrics.record_result(tc, None, error=None)
            except Exception as e:
                print(f"PASS (Safely blocked: {type(e).__name__})")
                metrics.record_result(tc, None, error=str(e))
            continue

        # 2. Follow-Up Query Handling
        if follow_up:
            try:
                # First turn
                process_query(session_id, question)
                # Second follow-up turn
                res = process_query(session_id, follow_up)
                print("PASS")
                metrics.record_result(tc, res, error=None)
            except Exception as e:
                print(f"FAIL ({e})")
                metrics.record_result(tc, None, error=str(e))
            continue

        # 3. Standard Query Handling
        try:
            res = process_query(session_id, question)
            print("PASS")
            metrics.record_result(tc, res, error=None)
        except Exception as e:
            print(f"FAIL ({e})")
            metrics.record_result(tc, None, error=str(e))

    summary = metrics.summary()

    print("\n==================================================")
    print("EVALUATION SUMMARY REPORT")
    print("==================================================")
    print(f"Total Test Cases:       {summary['total_test_cases']}")
    print(f"Passed:                 {summary['passed']}")
    print(f"Failed:                 {summary['failed']}")
    print(f"Overall Accuracy:       {summary['accuracy_percentage']}%")
    print(f"Security Block Rate:    {summary['security_rejection_rate']}%")
    print(f"Average Latency:        {summary['avg_latency_ms']} ms")
    print(f"P95 Latency:            {summary['p95_latency_ms']} ms")

    if summary["failure_details"]:
        print("\nFailures:")
        for f in summary["failure_details"]:
            print(f"  - [{f['id']}] {f['question']}: {f['reason']}")

    report_path = Path(__file__).parent / "eval_report.json"
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"\nFull evaluation report saved to: {report_path}")

    return summary

if __name__ == "__main__":
    run_evaluation()
