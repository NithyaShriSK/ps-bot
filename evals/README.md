# SkillQuery AI Evaluation Framework (Evals)

Systematic evaluation harness for benchmarking question understanding, semantic course taxonomy resolution, conversational memory, SQL generation accuracy, student counts, and security guardrails against PostgreSQL.

## Architecture

```
evals/
├── test_dataset.json   # 52 verified test cases with expected intents, counts, and categories
├── metrics.py          # Benchmark metrics calculator (accuracy, latencies, security)
├── llm_judge.py        # Qualitative answer faithfulness & formatting evaluator
├── test_queries.py     # Unittest suite for automated CI/regression testing
├── run_evals.py        # CLI benchmark runner
└── README.md           # Documentation and execution guide
```

## Running Evaluations

### 1. Execute Complete 52-Test Benchmark

```powershell
.\.venv\Scripts\python.exe evals\run_evals.py
```

Outputs live pass/fail status, detailed latency percentiles, and generates `evals/eval_report.json`.

### 2. Run Unit Tests

```powershell
.\.venv\Scripts\python.exe -m unittest evals\test_queries.py
```

## Evaluated Categories

1. **Category Queries**: Semantic resolution of high-level domains (Frontend, Backend, Database, Cloud/DevOps, AI/ML, Data Science, Mobile).
2. **Multi-Course Queries**: Cross-row AND logic (e.g. students who cleared both Python and Java).
3. **Department Filters**: Roll-number regex extraction and department matching (CSE, IT, ECE, AIDS, etc.).
4. **Student Rankings**: Deterministic aggregation and ranking by distinct course levels completed.
5. **Conversational Memory**: Multi-turn follow-ups (`"Show their names"`, `"What about CSE?"`).
6. **Security Guardrails**: Prevention of SQL injection, catalog probing, command chaining, and destructive operations.
