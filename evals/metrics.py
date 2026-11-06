"""
Evaluation metrics calculation for SkillQuery AI Evaluation Framework.
Computes intent accuracy, mapping precision, SQL validity, execution success,
security rejection rate, and execution latencies.
"""

from typing import List, Dict, Any

class EvalMetrics:
    def __init__(self):
        self.total = 0
        self.passed = 0
        self.failed = 0
        
        # Sub-metrics
        self.intent_matches = 0
        self.category_matches = 0
        self.sql_valid_count = 0
        self.sql_executed_count = 0
        self.count_exact_matches = 0
        self.security_blocked = 0
        self.security_total = 0
        self.latencies: List[int] = []
        self.failure_details: List[Dict[str, Any]] = []

    def record_result(self, test_case: Dict[str, Any], result: Dict[str, Any], error: str = None):
        self.total += 1
        tc_id = test_case.get("id")
        tc_cat = test_case.get("category")
        should_succeed = test_case.get("should_succeed", True)

        # Handle Security Rejection Cases
        if tc_cat == "security_test":
            self.security_total += 1
            if error is not None:
                self.security_blocked += 1
                self.passed += 1
            else:
                self.failed += 1
                self.failure_details.append({
                    "id": tc_id,
                    "category": tc_cat,
                    "question": test_case["question"],
                    "reason": "Security vulnerability: Unsafe query was not blocked!"
                })
            return

        # Normal Query Cases
        if error is not None:
            self.failed += 1
            self.failure_details.append({
                "id": tc_id,
                "category": tc_cat,
                "question": test_case["question"],
                "reason": f"Execution error: {error}"
            })
            return

        meta = result.get("meta", {})
        latency = meta.get("latency_ms", 0)
        self.latencies.append(latency)

        is_passed = True
        failure_reasons = []

        # 1. SQL Validity & Execution
        if meta.get("sql"):
            self.sql_valid_count += 1
            self.sql_executed_count += 1

        # 2. Category Mapping Accuracy
        expected_cat = test_case.get("expected_category")
        if expected_cat:
            actual_cat = meta.get("category")
            if actual_cat == expected_cat:
                self.category_matches += 1
            else:
                is_passed = False
                failure_reasons.append(f"Category mismatch: expected {expected_cat}, got {actual_cat}")

        # 3. Exact Count Verification (where independently known from database)
        expected_count = test_case.get("expected_count")
        if expected_count is not None:
            raw_answer = result.get("answer", "")
            # Check if count appears in bold line
            if f"**{expected_count:,} students**" in raw_answer or f"**{expected_count} students**" in raw_answer:
                self.count_exact_matches += 1
            else:
                is_passed = False
                failure_reasons.append(f"Student count mismatch: expected {expected_count}")

        # 4. Minimum Rows for Rankings/Lists
        expected_min_rows = test_case.get("expected_min_rows")
        if expected_min_rows:
            actual_rows = len(result.get("rows", []))
            if actual_rows < expected_min_rows:
                is_passed = False
                failure_reasons.append(f"Row count below threshold: expected >= {expected_min_rows}, got {actual_rows}")

        if is_passed:
            self.passed += 1
        else:
            self.failed += 1
            self.failure_details.append({
                "id": tc_id,
                "category": tc_cat,
                "question": test_case["question"],
                "reason": "; ".join(failure_reasons)
            })

    def summary(self) -> Dict[str, Any]:
        avg_latency = sum(self.latencies) / len(self.latencies) if self.latencies else 0
        sorted_lat = sorted(self.latencies)
        p95_latency = sorted_lat[int(len(sorted_lat) * 0.95)] if sorted_lat else 0

        acc = (self.passed / self.total * 100) if self.total else 0
        sec_rate = (self.security_blocked / self.security_total * 100) if self.security_total else 100

        return {
            "total_test_cases": self.total,
            "passed": self.passed,
            "failed": self.failed,
            "accuracy_percentage": round(acc, 2),
            "security_rejection_rate": round(sec_rate, 2),
            "avg_latency_ms": round(avg_latency, 1),
            "p95_latency_ms": p95_latency,
            "failure_details": self.failure_details
        }
