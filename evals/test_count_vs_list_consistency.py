"""
Regression Test Suite: Student Count vs Student List Inconsistency Invariant.
Verifies that for every student analytics query:
COUNT(DISTINCT roll_number) == Total unique students returned by listing query.
"""

import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(PROJECT_ROOT))

from query_engine import process_query

def run_tests():
    test_cases = [
        {
            "name": "Java in CSE Department (User Reported Issue)",
            "count_q": "How many students cleared Java in CSE department?",
            "list_q": "I want the list of students who cleared java in cse dept"
        },
        {
            "name": "Python in CSE Department",
            "count_q": "How many CSE students completed Python?",
            "list_q": "List CSE students who completed Python"
        },
        {
            "name": "C Programming Level 5 in CSE",
            "count_q": "how many students cleared C level 5 in CSE department",
            "list_q": "list students who cleared C level 5 in CSE department"
        },
        {
            "name": "Database Programming across University (>50 students)",
            "count_q": "How many students cleared Database Programming?",
            "list_q": "List students who cleared Database Programming"
        },
        {
            "name": "Data Structures / DSA",
            "count_q": "How many students cleared DSA?",
            "list_q": "List students who cleared DSA"
        },
        {
            "name": "Empty / Non-existent Technology Check",
            "count_q": "How many students cleared Ruby on Rails in Mechanical department?",
            "list_q": "List students who cleared Ruby on Rails in Mechanical department"
        }
    ]

    all_passed = True
    print("=" * 65)
    print("RUNNING COUNT VS LIST CONSISTENCY INVARIANT TESTS")
    print("=" * 65)

    for tc in test_cases:
        name = tc["name"]
        print(f"\n[TEST] {name}")
        
        # 1. Execute Count Query
        res_count = process_query("test_cnt", tc["count_q"])
        count_rows = res_count.get("rows", [])
        if count_rows and "student_count" in count_rows[0]:
            count_val = int(count_rows[0]["student_count"])
        else:
            count_val = 0
            
        # 2. Execute List Query
        res_list = process_query("test_lst", tc["list_q"])
        list_rows = res_list.get("rows", [])
        total_list_count = len(list_rows)
        
        # 3. Collect Unique Roll Numbers
        unique_rolls = set(r["roll_number"] for r in list_rows if "roll_number" in r)
        unique_count = len(unique_rolls)
        
        # 4. Check Invariant: Count == Total Listed == Unique Rolls
        passed = (count_val == total_list_count == unique_count)
        if not passed:
            all_passed = False
            
        print(f"  Count Query Output:       {count_val} students")
        print(f"  List Query Rows Fetched:  {total_list_count} rows")
        print(f"  Unique Roll Numbers:      {unique_count}")
        print(f"  Reported Answer Line 1:   {res_list['answer'].splitlines()[0]}")
        print(f"  INVARIANT STATUS:         {'PASSED' if passed else 'FAILED'}")

    print("\n" + "=" * 65)
    if all_passed:
        print("ALL COUNT VS LIST CONSISTENCY INVARIANTS PASSED (100%)")
    else:
        print("SOME TESTS FAILED")
    print("=" * 65)
    return all_passed

if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
