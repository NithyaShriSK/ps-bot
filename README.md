# SkillQuery: Student Skills Intelligence Assistant

Natural-language semantic querying and course taxonomy analytics for student course records using **PostgreSQL**, **Groq LLM**, and **FastAPI**, with dual interfaces for web dashboards and the **WhatsApp Cloud API**.

---

## 1. Key Capabilities

- **Semantic Skill Taxonomy**: Translates abstract skill categories (e.g. *Frontend*, *Backend*, *Programming Languages*, *Database*, *Full Stack*, *Cloud & DevOps*, *AI/ML*, *Data Science*, *Mobile*) into verified course completions in PostgreSQL rather than failing on exact name matches.
- **Conversational Memory**: Retains multi-turn session context (e.g. asking *"How many students completed frontend courses?"* followed by *"Show their names"*, then *"What about CSE?"*).
- **Guarded Read-Only Execution**: Strict transaction-level read-only enforcement, single-statement restrictions, statement timeouts, table allowlisting, and automated result row limits.
- **Student vs. Attempt Awareness**: Correctly distinguishes assessment attempts ($225,576$ rows) from unique student completions ($1,451$ students) using `COUNT(DISTINCT roll_number)`.
- **Automated AI Evaluation Framework (Evals)**: Continuous benchmarking suite with 52 test cases covering categories, rankings, conjunctions, follow-ups, and security injection attempts.

---

## 2. Architecture & File Structure

```
ps-bot/
├── app.py                  # FastAPI service hosting Web UI, REST API, and WhatsApp webhook
├── query_engine.py         # Semantic intent classification, SQL synthesis, and result synthesis
├── course_taxonomy.py      # Structured mapping of skill categories & departments to database records
├── session_memory.py       # Session-based conversational memory manager
├── db.py                   # Read-only PostgreSQL connection manager with pooler retries
├── sql_guard.py            # Security boundary protecting against injection and unapproved tables
├── schema.sql              # Database schema definitions & indexes
├── requirements.txt        # Python package dependencies
├── test.py                 # Interactive CLI terminal test utility
├── frontend/               # Web client interface
│   ├── index.html          # Semantic query dashboard
│   ├── app.js              # Interactive chat, rank tables, and Google Sheets/CSV export
│   └── styles.css          # Modern dark/light UI styling
└── evals/                  # AI Evaluation & Benchmark Suite
    ├── test_dataset.json   # 52 verified test cases with exact student counts
    ├── metrics.py          # Benchmark metrics calculator (accuracy, latencies, security)
    ├── llm_judge.py        # Qualitative LLM-as-judge evaluator
    ├── test_queries.py     # Unittest test suite
    ├── run_evals.py        # Benchmark execution runner
    └── README.md           # Evaluation documentation
```

---

## 3. Supported Skill Categories

| Category | Canonical Key | Courses & Subjects Included |
| :--- | :--- | :--- |
| **Frontend Development** | `frontend` | HTML / CSS, Java Script, React, UI/UX (Levels 1–5), Web Technology (CSE Core), Modern Web Applications |
| **Backend Development** | `backend` | Programming Python, Programming Java, Database Programming, DBMS Core Concepts, Data Structures, Linux, Computer Networks |
| **Programming Languages** | `programming_languages` | C Programming, Programming C++, Programming Java, Programming Python, Java Script |
| **Database Technologies** | `database` | Database Programming (Levels 1–7), DBMS Core Concepts (Levels 1–3) |
| **Full Stack Development** | `full_stack` | Full Stack & DevOps, Vibe Coding, Modern Web Applications, Cross-stack completions |
| **Cloud & DevOps** | `cloud_devops` | Linux, Version Control (Git & GitHub), Cloud & Cyber Security |
| **AI & Machine Learning** | `ai_ml` | Machine Learning, Deep Learning, Maths for Machine Learning, AI Development |
| **Data Science & Analytics** | `data_science` | Data Science, Bioinformatics & Data Analytics, Data Science Core Concepts |
| **Mobile App Development** | `mobile_development` | Mobile App Development - Android (Java), Mobile Application Design |

---

## 4. Setup and Local Execution

### 4.1 Prerequisites
- Python 3.10+
- PostgreSQL database (or Supabase connection string)

### 4.2 Installation
```powershell
# Create and activate virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# Install dependencies
pip install -r requirements.txt
```

### 4.3 Configure `.env`
Ensure `.env` contains:
```env
DATABASE_URL=postgresql://user:password@host:5432/postgres?sslmode=require
GROQ_API_KEY=gsk_your_groq_api_key
GROQ_MODEL=qwen/qwen3.8-27b
WHATSAPP_VERIFY_TOKEN=your_whatsapp_verify_token
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token
WHATSAPP_PHONE_NUMBER_ID=your_whatsapp_phone_number_id
META_GRAPH_VERSION=v22.0
```

### 4.4 Start the Web Server
```powershell
uvicorn app:app --host 0.0.0.0 --port 8000 --reload
```
Open [http://127.0.0.1:8000](http://127.0.0.1:8000) to access the SkillQuery web dashboard.

### 4.5 Run Interactive CLI Test
```powershell
python test.py
```

### 4.6 Run AI Evaluation Benchmark (52 Test Cases)
```powershell
python evals\run_evals.py
```

---

## 5. Security & Read-Only Governance

1. **Transaction Read-Only**: Every connection explicitly executes `SET TRANSACTION READ ONLY`.
2. **Statement Allowlisting**: Only `SELECT` or `WITH ... SELECT` queries are permitted. Multi-statement chaining (`...; DROP TABLE...`) is strictly rejected.
3. **Table Isolation**: Access is restricted strictly to approved tables (`ps_cleared_course_view`, `ps_department_code_map`, `ps_course_domain_map`, `ps_student_course_summary`).
4. **Row Bounds**: Safe automatic clamping of result row limits (maximum 100 rows).
5. **No Credential Leakage**: Database URLs and credentials are automatically scrubbed from client errors and logs.
