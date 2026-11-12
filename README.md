<div align="center">

# 🎓 SkillQuery

### Student Skills Intelligence Assistant

*Ask questions about student course records in plain English — get verified, exportable answers.*

[**🌐 Live Demo**](https://ps-bot-six.vercel.app/)

![Python](https://img.shields.io/badge/Python-3.10+-3776AB?logo=python&logoColor=white)
![FastAPI](https://img.shields.io/badge/FastAPI-009688?logo=fastapi&logoColor=white)
![PostgreSQL](https://img.shields.io/badge/PostgreSQL-4169E1?logo=postgresql&logoColor=white)
![Groq](https://img.shields.io/badge/LLM-Groq-F55036)
![WhatsApp](https://img.shields.io/badge/WhatsApp-Cloud%20API-25D366?logo=whatsapp&logoColor=white)
![Evals](https://img.shields.io/badge/evals-60%20cases%20%7C%20100%25-brightgreen)
![Security](https://img.shields.io/badge/SQL%20guard-read--only-blue)

[Overview](#-overview) •
[Features](#-key-capabilities) •
[Example Queries](#-example-queries) •
[Architecture](#-architecture) •
[Skill Categories](#-supported-skill-categories) •
[Getting Started](#-getting-started) •
[Evals](#-evaluation--testing) •
[Security](#-security--read-only-governance)

</div>

---

## 📖 Table of Contents

1. [Overview](#-overview)
2. [Key Capabilities](#-key-capabilities)
3. [Example Queries](#-example-queries)
4. [Architecture](#-architecture)
5. [Tech Stack](#-tech-stack)
6. [Supported Skill Categories](#-supported-skill-categories)
7. [Getting Started](#-getting-started)
8. [Evaluation & Testing](#-evaluation--testing)
9. [Security & Read-Only Governance](#-security--read-only-governance)
10. [Project Structure](#-project-structure)
11. [Roadmap](#-roadmap)

---

## 🎯 Overview

**SkillQuery** lets faculty and administrators query student course records using natural language. It combines **PostgreSQL**, a **Groq-hosted LLM** and **FastAPI** to turn questions like *"Top 10 students who cleared Python Level 3 in CSE"* into safe, verified SQL, with two interfaces:

- 🖥️ a **web dashboard** with paginated results and CSV / Google Sheets export,
- 💬 a **WhatsApp bot** via the WhatsApp Cloud API.

**Live app:** <https://ps-bot-six.vercel.app/>

<!-- Add a dashboard screenshot or GIF here -->
<!-- ![SkillQuery Dashboard](docs/images/dashboard.png) -->

---

## ✨ Key Capabilities

| Capability | What it does |
| --- | --- |
| 🧭 **Semantic skill taxonomy** | Maps abstract categories (*Frontend*, *Backend*, *DSA*, *AI/ML*, …) to verified course completions instead of failing on exact name matches |
| 🔁 **Canonical course equivalences** | Resolves aliases: *C* ≡ *C Programming*, *Java* ≡ *Programming Java*, *Python* ≡ *Programming Python*, *SQL* ≡ *Database Programming*, *DSA* ≡ *Data Structure using Java* |
| 🎚️ **Level filtering** | Understands targets like *"C level 5 in CSE"* or *"Python level 3"* |
| 🚫 **Completion-state intelligence** | Distinguishes completed, *didn't complete*, *attempted but not cleared*, *pending*, *some but not all*, and comparisons like *"cleared Python but not Java"* |
| ✅ **Single source of truth** | `COUNT(DISTINCT roll_number)` = unique listed students = exported students, always |
| 🏆 **Dynamic Top-N ranking** | Parses *"Top 5 in database"*, *"Top 50 who cleared C Level 2"*; returns cohort size alongside the ranked subset using `COUNT(*) OVER()` with deterministic tie-breaking (`roll_number ASC`) |
| 🧠 **Conversational memory** | Multi-turn context: *"How many completed backend?"* → *"List those who didn't"* → *"What about CSE?"* |
| 🏷️ **Cleared course / level display** | Shows exact courses and levels cleared via `string_agg(DISTINCT course_name, ', ')`, rendered as badge tags |
| 📄 **Pagination & export** | 50-per-page results with deterministic `ORDER BY roll_number ASC`; full-cohort CSV and Google Sheets export |
| 🔒 **Guarded execution** | Read-only transactions, single-statement rule, statement timeouts, table allowlist, 5,000-row cap |
| 📊 **Built-in evals** | 60-case benchmark plus invariant regression suites with **100 % accuracy** and **100 % security rejection** |

---

## 💬 Example Queries

```text
How many students completed backend courses?
List the students who didn't complete it.
What about CSE?

Top 50 students who cleared C Level 2
Top 10 Java students
Students who cleared Python but not Java
Who attempted but failed to clear database courses?
C level 5 in CSE
```

---

## 🏗️ Architecture

```mermaid
flowchart LR
    subgraph Clients
        WEB["Web Dashboard\n(frontend/)"]
        WA["WhatsApp Cloud API"]
    end

    subgraph Service ["FastAPI Service (app.py)"]
        QE["Query Engine\nIntent → SQL → Answer"]
        TAX["Course Taxonomy"]
        MEM["Session Memory"]
        GUARD["SQL Guard\nread-only · allowlist · limits"]
    end

    LLM["Groq LLM"]
    DB[("PostgreSQL\n/ Supabase")]

    WEB <--> Service
    WA <-->|Webhook| Service
    QE <--> TAX
    QE <--> MEM
    QE <--> LLM
    QE --> GUARD --> DB
```

**Flow:** question → session context → taxonomy resolution → LLM intent / SQL synthesis → **SQL guard validation** → read-only execution → result synthesis → paginated table or WhatsApp reply.

---

## 🧰 Tech Stack

| Layer | Technology |
| --- | --- |
| **Backend** | FastAPI, Uvicorn |
| **Database** | PostgreSQL (Supabase-compatible), `psycopg` |
| **LLM** | Groq Cloud |
| **Frontend** | HTML, CSS, vanilla JavaScript |
| **Messaging** | WhatsApp Cloud API (Meta Graph API) |
| **Deployment** | Vercel |
| **Evaluation** | Custom benchmark runner, LLM-as-judge, `unittest` |

---

## 📚 Supported Skill Categories

| Category | Key | Courses & subjects |
| --- | --- | --- |
| **Frontend Development** | `frontend` | HTML / CSS, JavaScript, React, UI/UX (L1–5), Web Technology (CSE Core), Modern Web Applications |
| **Backend Development** | `backend` | Node.js, Express.js, Django, Flask, Spring Boot, PHP *(strictly verified backend frameworks)* |
| **Programming Languages** | `programming_languages` | C, C++, Java, Python, JavaScript |
| **Database Management** | `database` | Database Programming (L1–7), DBMS Core Concepts (L1–3) |
| **Data Structures & Algorithms** | `dsa` | Data Structure (L1–6), DS Core Concepts (CSE), Data Structure using Java |
| **Operating Systems** | `os` | OS Core Concepts (CSE L1–3), RTOS |
| **Computer Networks** | `networks` | Computer Networking (L0–2), Networks Core Concepts (CSE), Networks & Protocols |
| **Linux & Systems** | `linux_systems` | Linux (L0–3) |
| **UI/UX Design** | `ui_ux` | UI/UX (L1–5), Web Design & UI Engineering |
| **Full Stack Development** | `full_stack` | Full Stack & DevOps, Vibe Coding, Modern Web Applications |
| **Cloud & DevOps** | `cloud_devops` | Linux, Git & GitHub, Cloud & Cyber Security |
| **AI & Machine Learning** | `ai_ml` | Machine Learning, Deep Learning, Maths for ML, AI Development |
| **Data Science & Analytics** | `data_science` | Data Science, Bioinformatics & Data Analytics, DS Core Concepts |
| **Mobile App Development** | `mobile_development` | Android (Java), Mobile Application Design |

---

## 🚀 Getting Started

### Prerequisites

- Python 3.10+
- A PostgreSQL database (or a Supabase connection string)
- A [Groq API key](https://console.groq.com/)
- *(Optional)* Meta WhatsApp Cloud API credentials

### 1. Clone

```bash
git clone https://github.com/boomiikas/skillquery.git
cd skillquery
```

### 2. Install

```bash
python -m venv .venv

# Windows (PowerShell)
.\.venv\Scripts\Activate.ps1
# macOS / Linux
# source .venv/bin/activate

pip install -r requirements.txt   # lightweight, ~50 MB
```

### 3. Configure `.env`

Copy `.env.example` to `.env`:

```env
DATABASE_URL=postgresql://user:password@host:5432/postgres?sslmode=require
GROQ_API_KEY=gsk_your_groq_api_key
GROQ_MODEL=your_groq_model_name
WHATSAPP_VERIFY_TOKEN=your_whatsapp_verify_token
WHATSAPP_ACCESS_TOKEN=your_whatsapp_access_token
WHATSAPP_PHONE_NUMBER_ID=your_whatsapp_phone_number_id
META_GRAPH_VERSION=v22.0
```

### 4. Set up the database

Apply `schema.sql` to your PostgreSQL instance. To load existing data from a MySQL dump, use `import_mysql_dump.py`, then build the semantic index with `embed_index.py`. See `sample_queries.sql` for reference queries.

### 5. Run

```bash
uvicorn app:app --host 127.0.0.1 --port 8000 --reload
```

Open <http://127.0.0.1:8000>.

A quick terminal test client is also available:

```bash
python test.py
```

---

## 📊 Evaluation & Testing

| Suite | Command | Verifies |
| --- | --- | --- |
| **Count = List = Export** | `python evals/test_count_vs_list_consistency.py` | Count queries and listings return identical totals across departments and courses |
| **Top-N & cohort sizing** | `python evals/test_ranking_limits.py` | Limit extraction (Top 5 / 10 / 25 / 50 / 100), cohort counts, tie-breaking |
| **Full benchmark** | `python evals/run_evals.py` | 60 verified cases: accuracy, latency and security rejection |

Evaluation helpers include `metrics.py` (accuracy, latency, security metrics) and `llm_judge.py` (qualitative LLM-as-judge). Full details are in [`evals/README.md`](evals/README.md).

---

## 🔒 Security & Read-Only Governance

1. **Read-only transactions.** Every connection runs `SET TRANSACTION READ ONLY`.
2. **Statement allowlisting.** Only `SELECT` or `WITH … SELECT` is allowed; multi-statement chaining (`…; DROP TABLE …`) is rejected.
3. **Table isolation.** Access is limited to `ps_cleared_course_view`, `ps_department_code_map`, `ps_course_domain_map` and `ps_student_course_summary`.
4. **Safe result limits.** A 5,000-row ceiling supports full-cohort analysis (1,451 students) while blocking abusive queries.
5. **No credential leakage.** Database URLs and secrets are scrubbed from client errors and logs.

---

## 📁 Project Structure

```
skillquery/
├── app.py                  # FastAPI service: web UI, REST API, WhatsApp webhook
├── query_engine.py         # Intent classification, SQL synthesis, result synthesis
├── course_taxonomy.py      # Skill categories & departments → database mapping
├── session_memory.py       # Conversational memory manager
├── db.py                   # Read-only PostgreSQL manager with pooler retries
├── sql_guard.py            # Injection / unapproved-table protection
├── embed_index.py          # Builds the semantic embedding index
├── import_mysql_dump.py    # Imports a MySQL dump into PostgreSQL
├── schema.sql              # Schema definitions & indexes
├── sample_queries.sql      # Reference SQL queries
├── test.py                 # Interactive CLI test utility
├── requirements.txt
├── .env.example
├── frontend/
│   ├── index.html          # Query dashboard
│   ├── app.js              # Chat, paginated tables, badges, CSV/Sheets export
│   └── styles.css          # UI styling
└── evals/
    ├── test_dataset.json   # 60 verified cases
    ├── test_ranking_limits.py
    ├── test_count_vs_list_consistency.py
    ├── metrics.py
    ├── llm_judge.py
    ├── test_queries.py
    ├── run_evals.py
    └── README.md
```

---

## 🗺️ Roadmap

- [ ] Role-based access for faculty vs. department heads
- [ ] Charts and trend analytics for cohort skill coverage
- [ ] Telegram / Slack channels
- [ ] Docker setup for one-command local runs

---

<div align="center">

⭐ If you find this useful, consider starring the repo!

</div>
