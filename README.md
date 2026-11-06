# SkillQuery: Student Skills Intelligence Assistant

**Live Web Application:** [https://ps-bot-six.vercel.app/](https://ps-bot-six.vercel.app/)

Natural-language semantic querying and course taxonomy analytics for student course records using **PostgreSQL**, **Groq LLM**, and **FastAPI**, with dual interfaces for web dashboards and the **WhatsApp Cloud API**.

---

## 1. Key Capabilities

- **Semantic Skill Taxonomy**: Translates abstract skill categories (e.g. *Frontend*, *Backend*, *Programming Languages*, *Database Management*, *DSA*, *Operating Systems*, *Computer Networks*, *Cloud & DevOps*, *AI/ML*, *Data Science*, *Mobile*) into verified course completions in PostgreSQL rather than failing on exact name matches.
- **Canonical Course Equivalences & Level Filtering**: Resolves common aliases seamlessly (*C* $\equiv$ *C Programming*, *Java* $\equiv$ *Programming Java*, *Python* $\equiv$ *Programming Python*, *SQL* $\equiv$ *Database Programming*, *DSA* $\equiv$ *Data Structure using Java*). Accurately parses course level targets (e.g. *"C level 5 in CSE"*, *"Python level 3"*).
- **Negative & Completion-State Intelligence**: Intelligently distinguishes between positive completions, *"didn't complete"*, *"attempted but failed to clear"*, *"pending assessments"*, partial completions (*"some but not all"*), and cross-skill comparisons (*"cleared Python but not Java"*).
- **Single Source of Truth & Pagination**: Guaranteed invariant:
  $$\text{COUNT(DISTINCT roll\_number)} = \text{Unique Listed Students} = \text{Exported Students}$$
  Interactive 50-per-page client pagination with deterministic ordering (`ORDER BY roll_number ASC`) and complete CSV / Google Sheets exports of the full matching student population.
- **Dynamic Top-N Ranking & Cohort Sizing**: Accurately parses user-requested ranking limits (*"Top 50 students who cleared C Level 2"*, *"Top 5 in database"*, *"Top 10 Java students"*). Computes total cohort population alongside ranked subsets using PostgreSQL window functions (`COUNT(*) OVER()`), applying transparent deterministic tie-breaking (`roll_number ASC`).
- **Conversational Memory**: Retains multi-turn session context (e.g. asking *"How many students completed backend courses?"* followed by *"List me the students who didn't complete it"*, or *"What about CSE?"*).
- **Cleared Course / Level Display**: Student rankings and lists display exact verified courses and levels cleared using `string_agg(DISTINCT course_name, ', ')` styled with responsive badge tags.
- **Guarded Read-Only Execution**: Strict transaction-level read-only enforcement (`SET TRANSACTION READ ONLY`), single-statement restrictions, statement timeouts, table allowlisting, and automated result row bounds (up to 5,000 rows).
- **Automated AI Evaluation Framework (Evals)**: Continuous benchmarking suite with 60 test cases and invariant regression suites achieving **100% accuracy** and **100% security rejection rate**.

---

## 2. Architecture & File Structure

```
ps-bot/
├── app.py                                   # FastAPI service hosting Web UI, REST API, and WhatsApp webhook
├── query_engine.py                          # Semantic intent classification, SQL synthesis, and result synthesis
├── course_taxonomy.py                       # Structured mapping of skill categories & departments to database records
├── session_memory.py                        # Session-based conversational memory manager
├── db.py                                    # Read-only PostgreSQL connection manager with pooler retries
├── sql_guard.py                             # Security boundary protecting against injection and unapproved tables
├── schema.sql                               # Database schema definitions & indexes
├── requirements.txt                         # Lightweight Python dependencies (FastAPI, psycopg, groq, etc.)
├── test.py                                  # Interactive CLI terminal test utility
├── frontend/                                # Web client interface
│   ├── index.html                           # Semantic query dashboard
│   ├── app.js                               # Interactive chat, paginated tables, badge tags, and CSV/Sheets export
│   └── styles.css                           # Modern UI styling with pill badges and pagination controls
└── evals/                                   # AI Evaluation & Benchmark Suite
    ├── test_dataset.json                    # 60 verified test cases with exact student counts and security tests
    ├── test_ranking_limits.py               # Regression suite verifying dynamic Top-N extraction and cohort counts
    ├── test_count_vs_list_consistency.py    # Regression suite verifying Count == List == Export invariant
    ├── metrics.py                           # Benchmark metrics calculator (accuracy, latencies, security)
    ├── llm_judge.py                         # Qualitative LLM-as-judge evaluator
    ├── test_queries.py                      # Unittest test suite
    ├── run_evals.py                         # Automated benchmark runner (60 test cases)
    └── README.md                            # Evaluation documentation
```

---

## 3. Supported Skill Categories

| Category | Canonical Key | Courses & Subjects Included |
| :--- | :--- | :--- |
| **Frontend Development** | `frontend` | HTML / CSS, Java Script, React, UI/UX (Levels 1–5), Web Technology (CSE Core), Modern Web Applications |
| **Backend Development** | `backend` | Node.js, Express.js, Django, Flask, Spring Boot, PHP backend *(strictly verified backend frameworks)* |
| **Programming Languages** | `programming_languages` | C Programming, Programming C++, Programming Java, Programming Python, Java Script |
| **Database Management** | `database` | Database Programming (Levels 1–7), DBMS Core Concepts (Levels 1–3) |
| **Data Structures & Algorithms** | `dsa` | Data Structure (Levels 1–6), Data Structure Core Concepts (CSE), Data Structure using Java |
| **Operating Systems** | `os` | Operating Systems Core Concepts (CSE Levels 1–3), Real-Time Operating Systems (RTOS) |
| **Computer Networks** | `networks` | Computer Networking (Levels 0–2), Networks Core Concepts (CSE), Computer Networks & Protocols |
| **Linux & Systems** | `linux_systems` | Linux (Levels 0–3) |
| **UI/UX Design** | `ui_ux` | UI/UX (Levels 1–5), Web Design & User Interface Engineering |
| **Full Stack Development** | `full_stack` | Full Stack & DevOps, Vibe Coding, Modern Web Applications |
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

# Install dependencies (lightweight ~50 MB, fast installation)
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
- **Live Deployment:** [https://ps-bot-six.vercel.app/](https://ps-bot-six.vercel.app/)
- **Local Development:**
```powershell
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```
Open [http://127.0.0.1:8000](http://127.0.0.1:8000) to access the SkillQuery web dashboard locally.

### 4.5 Run Invariant Consistency Regression Test
Verifies that count queries and student listings return identical totals across departments and courses:
```powershell
python evals\test_count_vs_list_consistency.py
```

### 4.6 Run Top-N Ranking & Limit Extraction Regression Test
Verifies dynamic limit extraction (Top 5, Top 10, Top 25, Top 50, Top 100), cohort sizing, and tie-breaking:
```powershell
python evals\test_ranking_limits.py
```

### 4.7 Run AI Evaluation Benchmark (60 Test Cases)
```powershell
python evals\run_evals.py
```

---

## 5. Security & Read-Only Governance

1. **Transaction Read-Only**: Every connection explicitly executes `SET TRANSACTION READ ONLY`.
2. **Statement Allowlisting**: Only `SELECT` or `WITH ... SELECT` queries are permitted. Multi-statement chaining (`...; DROP TABLE...`) is strictly rejected.
3. **Table Isolation**: Access is restricted strictly to approved tables (`ps_cleared_course_view`, `ps_department_code_map`, `ps_course_domain_map`, `ps_student_course_summary`).
4. **Safe Result Limits**: Default safe ceiling of 5,000 rows, allowing full university cohort analysis (1,451 students) while preventing denial-of-service queries.
5. **No Credential Leakage**: Database URLs and credentials are automatically scrubbed from client errors and logs.
