"""
SkillQuery Intelligent Query Engine.
Supports first-class positive and negative analytics:
- COMPLETED: Students who cleared a course/category
- NOT_COMPLETED: Students in universe who never completed a course/category
- ATTEMPTED_NOT_CLEARED: Students who attempted but never cleared
- PARTIAL: Students who completed some courses in a category but not all
- PENDING: Students with assessments pending results
- COMPARISON: Students who completed course A but not course B
- RANK: Students ranked by distinct completed levels
"""

import os
import re
import time
import json
from typing import Dict, Any, Tuple, Optional, List
from groq import Groq
from dotenv import load_dotenv

from db import fetch_rows
from sql_guard import validate_sql
from course_taxonomy import (
    TAXONOMY, DEPARTMENTS, resolve_category, resolve_department, get_taxonomy_summary
)
from session_memory import session_manager

load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = os.getenv("GROQ_MODEL", "qwen/qwen3.8-27b")

SCHEMA_PROMPT = """
Approved PostgreSQL table: ps_cleared_course_view
Columns:
  roll_number text, name text, vertical_name text, course_name text,
  date date, start_time time, end_time time, venue_name text, status text.

CRITICAL RULES:
1. Each row represents an assessment attempt.
2. For student counts, ALWAYS use COUNT(DISTINCT roll_number). Never use COUNT(*).
3. Status values: 'Cleared', 'Not Cleared', 'Pending for Result'.
4. Department code is in roll_number (e.g., '7376231CS101' -> 'CS' for Computer Science):
   Filter CSE: substring(roll_number from '^[0-9]{4}[0-9]{2}[0-9]([A-Za-z]+)') ILIKE 'CS'
5. Only SELECT queries. Always include a safe LIMIT <= 100.
"""

# ==============================================================================
# INTENT & SEMANTIC PARSING
# ==============================================================================

def detect_completion_intent(query: str) -> str:
    """Classifies the completion semantics (positive, negative, partial, pending, comparison)."""
    q = f" {query.lower()} "

    # 1. Partial Completion Intent (Must precede general 'but not')
    if re.search(r"\b(some .+ but not all|partially completed|partial|some of)\b", q):
        return "PARTIAL"

    # 2. Attempted but Failed Intent
    if re.search(r"\b(attempted (but|and) (failed|not cleared|didn'?t clear)|failed to clear|attempted but not cleared|tried but failed)\b", q):
        return "ATTEMPTED_NOT_CLEARED"

    # 3. Pending Intent
    if re.search(r"\b(pending|awaiting results|awaiting result|pending for result)\b", q):
        return "PENDING"

    # 4. Comparison Intent (e.g., Python but not Java)
    if extract_comparison_targets(query):
        return "COMPARISON"

    # 5. Negative Completion (Never cleared / didn't complete)
    if re.search(r"\b(didn'?t complete|did not complete|have not completed|haven'?t completed|never completed|didn'?t clear|did not clear|haven'?t cleared|have not cleared|never cleared|not completed|not cleared|who haven'?t|who didn'?t|haven'?t completed any|not completed any)\b", q):
        return "NOT_COMPLETED"

    # 6. Default Positive Completion
    return "COMPLETED"

def detect_output_format(query: str) -> str:
    """Classifies the expected output structure (COUNT, LIST, RANK)."""
    q = query.lower().strip()
    if re.search(r"\b(top\s+\d+|rank|leading|highest|best|most)\b", q):
        return "RANK"
    if re.search(r"\b(how\s+m[a-z]+|count|number\s+of|total\s+students)\b", q):
        return "COUNT"
    if re.search(r"\b(who|list|show|find|display|get|names|which students)\b", q):
        return "LIST"
    return "COUNT"

def extract_course_level(query: str) -> Optional[str]:
    """Extracts course level from query (e.g. 'level 5', 'level-5', 'lvl 2', 'level 3A')."""
    m = re.search(r"\b(?:level|lvl)\s*[-–]?\s*([0-9]+[a-z]?|[a-z])\b", query, re.IGNORECASE)
    if m:
        return m.group(1).lower()
    return None

CANONICAL_COURSES: Dict[str, Dict[str, Any]] = {
    "C Programming": {
        "display_name": "C Programming",
        "category": "programming_languages",
        "sql_condition": "(vertical_name ILIKE '%C Programming%' OR course_name ILIKE '%C Programming%')"
    },
    "Programming Java": {
        "display_name": "Programming Java",
        "category": "programming_languages",
        "sql_condition": "(vertical_name ILIKE '%Programming Java%' OR course_name ILIKE '%Programming Java%')"
    },
    "Programming Python": {
        "display_name": "Programming Python",
        "category": "programming_languages",
        "sql_condition": "(vertical_name ILIKE '%Programming Python%' OR course_name ILIKE '%Programming Python%')"
    },
    "Database Programming": {
        "display_name": "Database Programming",
        "category": "database",
        "sql_condition": "(vertical_name IN ('Database Programming', 'DBMS - Core Concept (PS-CSE)') OR course_name ILIKE '%Database Programming%' OR course_name ILIKE '%DBMS%')"
    },
    "Data Structures": {
        "display_name": "Data Structures",
        "category": "dsa",
        "sql_condition": "(vertical_name ILIKE '%Data Structure%' OR course_name ILIKE '%Data Structure%')"
    },
    "Programming C++": {
        "display_name": "Programming C++",
        "category": "programming_languages",
        "sql_condition": "(vertical_name ILIKE '%Programming C++%' OR course_name ILIKE '%Programming C++%')"
    },
    "Java Script": {
        "display_name": "Java Script",
        "category": "frontend",
        "sql_condition": "(vertical_name ILIKE '%Java Script%' OR course_name ILIKE '%Java Script%')"
    },
    "HTML / CSS": {
        "display_name": "HTML / CSS",
        "category": "frontend",
        "sql_condition": "(vertical_name ILIKE '%HTML / CSS%' OR course_name ILIKE '%HTML / CSS%')"
    },
    "React": {
        "display_name": "React",
        "category": "frontend",
        "sql_condition": "(vertical_name ILIKE '%React%' OR course_name ILIKE '%React%')"
    },
    "Linux": {
        "display_name": "Linux",
        "category": "linux_systems",
        "sql_condition": "(vertical_name ILIKE '%Linux%' OR course_name ILIKE '%Linux%')"
    },
    "Web Technology": {
        "display_name": "Web Technology",
        "category": "frontend",
        "sql_condition": "(vertical_name ILIKE '%Web Technology%' OR course_name ILIKE '%Web Technology%')"
    },
    "UI/UX": {
        "display_name": "UI/UX Design",
        "category": "ui_ux",
        "sql_condition": "(vertical_name ILIKE '%UI UX%' OR course_name ILIKE '%UI/UX%' OR course_name ILIKE '%User Interface%')"
    }
}

def extract_comparison_targets(query: str) -> Optional[Tuple[str, str]]:
    """Detects 'X but not Y' course comparisons."""
    q = query.lower()
    m = re.search(r'\b(?:but\s+not|without)\b', q)
    if not m:
        return None
    before = q[:m.start()]
    after = q[m.end():]
    tb = extract_course_entities(before)
    ta = extract_course_entities(after)
    if tb and ta and tb[-1] != ta[0]:
        return tb[-1], ta[0]
    return None

def resolve_tech_name(tech: str) -> Optional[str]:
    """Normalizes tech search string into database vertical or course pattern."""
    t = tech.lower().strip()
    mapping = {
        "python": "Programming Python",
        "programming python": "Programming Python",
        "java": "Programming Java",
        "programming java": "Programming Java",
        "c++": "Programming C++",
        "cpp": "Programming C++",
        "programming c++": "Programming C++",
        "c": "C Programming",
        "c programming": "C Programming",
        "c language": "C Programming",
        "javascript": "Java Script",
        "java script": "Java Script",
        "js": "Java Script",
        "react": "React",
        "html": "HTML / CSS",
        "css": "HTML / CSS",
        "html/css": "HTML / CSS",
        "html / css": "HTML / CSS",
        "sql": "Database Programming",
        "database": "Database Programming",
        "database programming": "Database Programming",
        "dbms": "Database Programming",
        "data structures": "Data Structures",
        "data structure": "Data Structures",
        "dsa": "Data Structures",
        "data structure using java": "Data Structures",
        "linux": "Linux",
        "node": "Node.js",
        "nodejs": "Node.js",
        "express": "Express.js",
        "django": "Django",
        "flask": "Flask"
    }
    return mapping.get(t)

def extract_course_entities(query: str) -> List[str]:
    """Detects specific database courses mentioned in query."""
    q = f" {query.lower()} "
    known_techs = [
        # Data Structures / DSA / Data Structure using Java (User requirement: all same)
        ("data structure using java", "Data Structures"),
        ("data structures using java", "Data Structures"),
        ("data structures and algorithms", "Data Structures"),
        ("data structures", "Data Structures"),
        ("data structure", "Data Structures"),
        ("dsa", "Data Structures"),

        # Database / SQL / Database Programming (User requirement: all same)
        ("database programming", "Database Programming"),
        ("sql", "Database Programming"),
        ("dbms", "Database Programming"),

        # C / C Programming (User requirement: both same)
        ("embedded c programming", "C Programming"),
        ("embedded c", "C Programming"),
        ("c programming", "C Programming"),
        ("c language", "C Programming"),
        ("c-programming", "C Programming"),

        # C++ / Programming C++
        ("programming c++", "Programming C++"),
        ("c++ programming", "Programming C++"),
        ("c++", "Programming C++"),
        ("cpp", "Programming C++"),

        # Java / Programming Java (User requirement: both same)
        ("programming java", "Programming Java"),
        ("java programming", "Programming Java"),
        ("java", "Programming Java"),

        # Python / Programming Python (User requirement: both same)
        ("programming python", "Programming Python"),
        ("python programming", "Programming Python"),
        ("python", "Programming Python"),

        # HTML / CSS
        ("html / css", "HTML / CSS"),
        ("html and css", "HTML / CSS"),
        ("html/css", "HTML / CSS"),
        ("html", "HTML / CSS"),
        ("css", "HTML / CSS"),

        # JavaScript
        ("java script", "Java Script"),
        ("javascript", "Java Script"),
        ("js", "Java Script"),

        # React
        ("react.js", "React"),
        ("reactjs", "React"),
        ("react", "React"),

        # Backend frameworks
        ("node.js", "Node.js"),
        ("nodejs", "Node.js"),
        ("node", "Node.js"),
        ("express.js", "Express.js"),
        ("expressjs", "Express.js"),
        ("express", "Express.js"),
        ("django", "Django"),
        ("flask", "Flask"),
        ("spring boot", "Spring Boot"),

        # Other core courses
        ("web technology", "Web Technology"),
        ("deep learning", "Deep Learning"),
        ("machine learning", "Machine Learning"),
        ("linux", "Linux"),

        # Single letter C (User requirement: C and C Programming both same)
        ("c", "C Programming")
    ]
    found = []
    for kw, target in known_techs:
        # Avoid matching 'java' when inside 'javascript' or 'data structure using java'
        if kw == "java":
            if "Data Structures" in found and re.search(r"\bdata\s+structures?\s+using\s+java\b", q):
                continue
            pattern = r"\bjava\b(?!\s*script)"
        # Avoid matching 'c' when C++ or C Programming already resolved
        elif kw == "c":
            if "Programming C++" in found or "C Programming" in found:
                continue
            pattern = r"\bc\b"
        elif kw in ("c++", "cpp"):
            pattern = r"(?:\b|\s)" + re.escape(kw) + r"(?:\b|\s)"
        else:
            pattern = r"(?:\b|\s)" + re.escape(kw) + r"(?:\b|\s)"

        if re.search(pattern, q):
            if target not in found:
                found.append(target)
    return found

# ==============================================================================
# DETERMINISTIC SQL SYNTHESIZERS
# ==============================================================================

def build_category_sql(
    category_key: str, 
    completion_intent: str,
    output_format: str,
    dept_code: Optional[str] = None, 
    level: Optional[str] = None,
    limit: int = 50
) -> Tuple[str, str]:
    """Builds SQL query for positive, negative, partial, or pending category queries with optional level filtering."""
    cat = TAXONOMY[category_key]
    condition = cat["sql_condition"]
    total_courses = len(cat.get("courses", [])) or 10

    dept_filter_main = ""
    dept_filter_s = ""
    if dept_code:
        dept_filter_main = f"AND substring(roll_number from '^[0-9]{{4}}[0-9]{{2}}[0-9]([A-Za-z]+)') ILIKE '{dept_code}'"
        dept_filter_s = f"AND substring(s.roll_number from '^[0-9]{{4}}[0-9]{{2}}[0-9]([A-Za-z]+)') ILIKE '{dept_code}'"

    level_filter = ""
    level_filter_c = ""
    level_str = f" Level {level.upper()}" if level else ""
    if level:
        level_filter = f"AND (course_name ILIKE '%Level%{level}%' OR course_name ILIKE '%- {level}%' OR course_name ILIKE '%-{level}%')"
        level_filter_c = f"AND (c.course_name ILIKE '%Level%{level}%' OR c.course_name ILIKE '%- {level}%' OR c.course_name ILIKE '%-{level}%')"

    # 1. NOT_COMPLETED (Students who have NEVER cleared any course in category)
    if completion_intent == "NOT_COMPLETED":
        if output_format == "COUNT":
            sql = f"""
                SELECT COUNT(DISTINCT s.roll_number) AS student_count
                FROM ps_cleared_course_view s
                WHERE NOT EXISTS (
                    SELECT 1 FROM ps_cleared_course_view c
                    WHERE c.roll_number = s.roll_number
                      AND c.status ILIKE 'Cleared'
                      AND {condition.replace('vertical_name', 'c.vertical_name').replace('course_name', 'c.course_name')}
                      {level_filter_c}
                )
                {dept_filter_s}
            """
            metric = f"Students in universe who have NOT completed any course in {cat['display_name']}{level_str}"
        else:
            sql = f"""
                SELECT DISTINCT s.roll_number, s.name,
                       substring(s.roll_number from '^[0-9]{{4}}[0-9]{{2}}[0-9]([A-Za-z]+)') AS dept_code
                FROM ps_cleared_course_view s
                WHERE NOT EXISTS (
                    SELECT 1 FROM ps_cleared_course_view c
                    WHERE c.roll_number = s.roll_number
                      AND c.status ILIKE 'Cleared'
                      AND {condition.replace('vertical_name', 'c.vertical_name').replace('course_name', 'c.course_name')}
                      {level_filter_c}
                )
                {dept_filter_s}
                ORDER BY s.roll_number ASC
                LIMIT {min(limit, 2000)}
            """
            metric = f"Students who have NOT completed any course in {cat['display_name']}{level_str}"
        return validate_sql(sql), metric

    # 2. ATTEMPTED_NOT_CLEARED (Students who attempted but failed to clear)
    elif completion_intent == "ATTEMPTED_NOT_CLEARED":
        if output_format == "COUNT":
            sql = f"""
                SELECT COUNT(*) AS student_count
                FROM (
                    SELECT roll_number
                    FROM ps_cleared_course_view
                    WHERE {condition}
                      {level_filter}
                      {dept_filter_main}
                    GROUP BY roll_number
                    HAVING COUNT(CASE WHEN status ILIKE 'Cleared' THEN 1 END) = 0
                ) sub
            """
            metric = f"Students who attempted courses in {cat['display_name']}{level_str} but have not cleared them"
        else:
            sql = f"""
                SELECT roll_number, name,
                       substring(roll_number from '^[0-9]{{4}}[0-9]{{2}}[0-9]([A-Za-z]+)') AS dept_code,
                       COUNT(*) AS attempts_recorded,
                       string_agg(DISTINCT course_name, ', ' ORDER BY course_name) AS attempted_courses
                FROM ps_cleared_course_view
                WHERE {condition}
                  {level_filter}
                  {dept_filter_main}
                GROUP BY roll_number, name
                HAVING COUNT(CASE WHEN status ILIKE 'Cleared' THEN 1 END) = 0
                ORDER BY roll_number ASC
                LIMIT {min(limit, 2000)}
            """
            metric = f"Students who attempted courses in {cat['display_name']}{level_str} but have not cleared any"
        return validate_sql(sql), metric

    # 3. PARTIAL (Completed some courses, but not all)
    elif completion_intent == "PARTIAL":
        if output_format == "COUNT":
            sql = f"""
                SELECT COUNT(*) AS student_count
                FROM (
                    SELECT roll_number
                    FROM ps_cleared_course_view
                    WHERE status ILIKE 'Cleared'
                      AND {condition}
                      {level_filter}
                      {dept_filter_main}
                    GROUP BY roll_number
                    HAVING COUNT(DISTINCT course_name) >= 1
                       AND COUNT(DISTINCT course_name) < {total_courses}
                ) sub
            """
            metric = f"Students who cleared some courses in {cat['display_name']}{level_str} but not all"
        else:
            sql = f"""
                SELECT roll_number, name,
                       substring(roll_number from '^[0-9]{{4}}[0-9]{{2}}[0-9]([A-Za-z]+)') AS dept_code,
                       COUNT(DISTINCT course_name) AS completed_levels,
                       string_agg(DISTINCT course_name, ', ' ORDER BY course_name) AS cleared_courses
                FROM ps_cleared_course_view
                WHERE status ILIKE 'Cleared'
                  AND {condition}
                  {level_filter}
                  {dept_filter_main}
                GROUP BY roll_number, name
                HAVING COUNT(DISTINCT course_name) >= 1
                   AND COUNT(DISTINCT course_name) < {total_courses}
                ORDER BY roll_number ASC
                LIMIT {min(limit, 2000)}
            """
            metric = f"Students who partially completed courses in {cat['display_name']}{level_str}"
        return validate_sql(sql), metric

    # 4. PENDING (Awaiting results)
    elif completion_intent == "PENDING":
        if output_format == "COUNT":
            sql = f"""
                SELECT COUNT(DISTINCT roll_number) AS student_count
                FROM ps_cleared_course_view
                WHERE status ILIKE 'Pending for Result'
                  AND {condition}
                  {level_filter}
                  {dept_filter_main}
            """
            metric = f"Students with pending assessments in {cat['display_name']}{level_str}"
        else:
            sql = f"""
                SELECT DISTINCT roll_number, name, course_name, venue_name, date, status,
                       substring(roll_number from '^[0-9]{{4}}[0-9]{{2}}[0-9]([A-Za-z]+)') AS dept_code
                FROM ps_cleared_course_view
                WHERE status ILIKE 'Pending for Result'
                  AND {condition}
                  {level_filter}
                  {dept_filter_main}
                ORDER BY roll_number ASC
                LIMIT {min(limit, 2000)}
            """
            metric = f"Pending assessments in {cat['display_name']}{level_str}"
        return validate_sql(sql), metric

    # 5. POSITIVE COMPLETED (Default)
    else:
        if output_format == "COUNT":
            sql = f"""
                SELECT COUNT(DISTINCT roll_number) AS student_count
                FROM ps_cleared_course_view
                WHERE status ILIKE 'Cleared'
                  AND {condition}
                  {level_filter}
                  {dept_filter_main}
            """
            metric = f"Distinct students who completed at least one course in {cat['display_name']}{level_str}"
        elif output_format == "RANK":
            sql = f"""
                SELECT roll_number, name,
                       substring(roll_number from '^[0-9]{{4}}[0-9]{{2}}[0-9]([A-Za-z]+)') AS dept_code,
                       COUNT(DISTINCT course_name) AS completed_levels,
                       string_agg(DISTINCT course_name, ', ' ORDER BY course_name) AS cleared_courses
                FROM ps_cleared_course_view
                WHERE status ILIKE 'Cleared'
                  AND {condition}
                  {level_filter}
                  {dept_filter_main}
                GROUP BY roll_number, name
                ORDER BY completed_levels DESC, roll_number ASC
                LIMIT {min(limit, 100)}
            """
            metric = f"Ranked by number of distinct course levels completed in {cat['display_name']}{level_str}"
        else:
            sql = f"""
                SELECT roll_number, name,
                       substring(roll_number from '^[0-9]{{4}}[0-9]{{2}}[0-9]([A-Za-z]+)') AS dept_code,
                       COUNT(DISTINCT course_name) AS completed_levels,
                       string_agg(DISTINCT course_name, ', ' ORDER BY course_name) AS cleared_courses
                FROM ps_cleared_course_view
                WHERE status ILIKE 'Cleared'
                  AND {condition}
                  {level_filter}
                  {dept_filter_main}
                GROUP BY roll_number, name
                ORDER BY roll_number ASC
                LIMIT {min(limit, 2000)}
            """
            metric = f"Students with distinct completed course levels in {cat['display_name']}{level_str}"
        return validate_sql(sql), metric

def build_single_or_multi_course_sql(
    targets: List[str], 
    completion_intent: str,
    output_format: str,
    dept_code: Optional[str] = None, 
    level: Optional[str] = None,
    limit: int = 50
) -> Tuple[str, str]:
    """Builds SQL for specific courses supporting positive/negative intents, ranking with levels, and optional level filtering."""
    dept_filter_main = ""
    dept_filter_s = ""
    if dept_code:
        dept_filter_main = f"AND substring(roll_number from '^[0-9]{{4}}[0-9]{{2}}[0-9]([A-Za-z]+)') ILIKE '{dept_code}'"
        dept_filter_s = f"AND substring(s.roll_number from '^[0-9]{{4}}[0-9]{{2}}[0-9]([A-Za-z]+)') ILIKE '{dept_code}'"

    level_filter = ""
    level_filter_c = ""
    level_str = f" Level {level.upper()}" if level else ""
    if level:
        level_filter = f"AND (course_name ILIKE '%Level%{level}%' OR course_name ILIKE '%- {level}%' OR course_name ILIKE '%-{level}%')"
        level_filter_c = f"AND (c.course_name ILIKE '%Level%{level}%' OR c.course_name ILIKE '%- {level}%' OR c.course_name ILIKE '%-{level}%')"

    # Helper to resolve sql condition for canonical courses
    def get_course_clause(t: str, prefix: str = "") -> str:
        col_v = f"{prefix}vertical_name" if prefix else "vertical_name"
        col_c = f"{prefix}course_name" if prefix else "course_name"
        if t in CANONICAL_COURSES:
            cond = CANONICAL_COURSES[t]["sql_condition"]
            if prefix:
                cond = cond.replace("vertical_name", col_v).replace("course_name", col_c)
            return cond
        return f"({col_v} ILIKE '%{t}%' OR {col_c} ILIKE '%{t}%')"

    # Single course
    if len(targets) == 1:
        t = targets[0]
        course_clause = get_course_clause(t)
        course_clause_c = get_course_clause(t, prefix="c.")
        display_name = f"{t}{level_str}"

        if completion_intent == "NOT_COMPLETED":
            if output_format == "COUNT":
                sql = f"""
                    SELECT COUNT(DISTINCT s.roll_number) AS student_count
                    FROM ps_cleared_course_view s
                    WHERE NOT EXISTS (
                        SELECT 1 FROM ps_cleared_course_view c
                        WHERE c.roll_number = s.roll_number
                          AND c.status ILIKE 'Cleared'
                          AND {course_clause_c}
                          {level_filter_c}
                    )
                    {dept_filter_s}
                """
                metric = f"Students who have not cleared {display_name}"
            else:
                sql = f"""
                    SELECT DISTINCT s.roll_number, s.name,
                           substring(s.roll_number from '^[0-9]{{4}}[0-9]{{2}}[0-9]([A-Za-z]+)') AS dept_code
                    FROM ps_cleared_course_view s
                    WHERE NOT EXISTS (
                        SELECT 1 FROM ps_cleared_course_view c
                        WHERE c.roll_number = s.roll_number
                          AND c.status ILIKE 'Cleared'
                          AND {course_clause_c}
                          {level_filter_c}
                    )
                    {dept_filter_s}
                    ORDER BY s.roll_number ASC
                    LIMIT {min(limit, 2000)}
                """
                metric = f"Students who have not cleared {display_name}"

        elif completion_intent == "ATTEMPTED_NOT_CLEARED":
            if output_format == "COUNT":
                sql = f"""
                    SELECT COUNT(*) AS student_count
                    FROM (
                        SELECT roll_number
                        FROM ps_cleared_course_view
                        WHERE {course_clause}
                          {level_filter}
                          {dept_filter_main}
                        GROUP BY roll_number
                        HAVING COUNT(CASE WHEN status ILIKE 'Cleared' THEN 1 END) = 0
                    ) sub
                """
                metric = f"Students who attempted {display_name} but never cleared it"
            else:
                sql = f"""
                    SELECT roll_number, name,
                           substring(roll_number from '^[0-9]{{4}}[0-9]{{2}}[0-9]([A-Za-z]+)') AS dept_code,
                           COUNT(*) AS attempts,
                           string_agg(DISTINCT course_name, ', ' ORDER BY course_name) AS attempted_courses
                    FROM ps_cleared_course_view
                    WHERE {course_clause}
                      {level_filter}
                      {dept_filter_main}
                    GROUP BY roll_number, name
                    HAVING COUNT(CASE WHEN status ILIKE 'Cleared' THEN 1 END) = 0
                    ORDER BY roll_number ASC
                    LIMIT {min(limit, 2000)}
                """
                metric = f"Students who attempted {display_name} but never cleared it"

        elif completion_intent == "PENDING":
            if output_format == "COUNT":
                sql = f"""
                    SELECT COUNT(DISTINCT roll_number) AS student_count
                    FROM ps_cleared_course_view
                    WHERE status ILIKE 'Pending for Result'
                      AND {course_clause}
                      {level_filter}
                      {dept_filter_main}
                """
                metric = f"Students with pending results for {display_name}"
            else:
                sql = f"""
                    SELECT DISTINCT roll_number, name, course_name, venue_name, date, status,
                           substring(roll_number from '^[0-9]{{4}}[0-9]{{2}}[0-9]([A-Za-z]+)') AS dept_code
                    FROM ps_cleared_course_view
                    WHERE status ILIKE 'Pending for Result'
                      AND {course_clause}
                      {level_filter}
                      {dept_filter_main}
                    ORDER BY roll_number ASC
                    LIMIT {min(limit, 2000)}
                """
                metric = f"Pending assessments for {display_name}"

        else: # COMPLETED
            if output_format == "COUNT":
                sql = f"""
                    SELECT COUNT(DISTINCT roll_number) AS student_count
                    FROM ps_cleared_course_view
                    WHERE status ILIKE 'Cleared'
                      AND {course_clause}
                      {level_filter}
                      {dept_filter_main}
                """
                metric = f"Students who cleared {display_name}"
            elif output_format == "RANK":
                sql = f"""
                    SELECT roll_number, name,
                           substring(roll_number from '^[0-9]{{4}}[0-9]{{2}}[0-9]([A-Za-z]+)') AS dept_code,
                           COUNT(DISTINCT course_name) AS completed_levels,
                           string_agg(DISTINCT course_name, ', ' ORDER BY course_name) AS cleared_courses
                    FROM ps_cleared_course_view
                    WHERE status ILIKE 'Cleared'
                      AND {course_clause}
                      {level_filter}
                      {dept_filter_main}
                    GROUP BY roll_number, name
                    ORDER BY completed_levels DESC, roll_number ASC
                    LIMIT {min(limit, 100)}
                """
                metric = f"Ranked by completed levels in {display_name}"
            else:
                sql = f"""
                    SELECT roll_number, name,
                           substring(roll_number from '^[0-9]{{4}}[0-9]{{2}}[0-9]([A-Za-z]+)') AS dept_code,
                           COUNT(DISTINCT course_name) AS completed_levels,
                           string_agg(DISTINCT course_name, ', ' ORDER BY course_name) AS cleared_courses
                    FROM ps_cleared_course_view
                    WHERE status ILIKE 'Cleared'
                      AND {course_clause}
                      {level_filter}
                      {dept_filter_main}
                    GROUP BY roll_number, name
                    ORDER BY roll_number ASC
                    LIMIT {min(limit, 2000)}
                """
                metric = f"Students who cleared {display_name}"
        return validate_sql(sql), metric

    # Multiple targets (AND conjunction across rows)
    filter_clauses = " OR ".join(get_course_clause(t) for t in targets)
    having_clauses = " AND ".join(
        f"COUNT(DISTINCT CASE WHEN {get_course_clause(t)} THEN 1 END) >= 1" 
        for t in targets
    )
    if output_format == "COUNT":
        sql = f"""
            SELECT COUNT(*) AS student_count
            FROM (
                SELECT roll_number
                FROM ps_cleared_course_view
                WHERE status ILIKE 'Cleared'
                  AND ({filter_clauses})
                  {dept_filter_main}
                GROUP BY roll_number
                HAVING {having_clauses}
            ) sub
        """
        metric = f"Students who cleared all requested courses: {', '.join(targets)}"
    else:
        sql = f"""
            SELECT roll_number, name,
                   substring(roll_number from '^[0-9]{{4}}[0-9]{{2}}[0-9]([A-Za-z]+)') AS dept_code,
                   COUNT(DISTINCT course_name) AS total_levels_cleared,
                   string_agg(DISTINCT course_name, ', ' ORDER BY course_name) AS cleared_courses
            FROM ps_cleared_course_view
            WHERE status ILIKE 'Cleared'
              AND ({filter_clauses})
              {dept_filter_main}
            GROUP BY roll_number, name
            HAVING {having_clauses}
            ORDER BY roll_number ASC
            LIMIT {min(limit, 2000)}
        """
        metric = f"Students who cleared each of: {', '.join(targets)}"
    return validate_sql(sql), metric

def build_comparison_sql(
    tech1: str, 
    tech2: str, 
    output_format: str,
    dept_code: Optional[str] = None, 
    limit: int = 50
) -> Tuple[str, str]:
    """Builds SQL for 'Students who completed tech1 but NOT tech2'."""
    dept_filter = ""
    if dept_code:
        dept_filter = f"AND substring(roll_number from '^[0-9]{{4}}[0-9]{{2}}[0-9]([A-Za-z]+)') ILIKE '{dept_code}'"

    def get_cond(t: str) -> str:
        if t in CANONICAL_COURSES:
            return CANONICAL_COURSES[t]["sql_condition"]
        return f"(vertical_name ILIKE '%{t}%' OR {col_c} ILIKE '%{t}%')"

    t1_clause = get_cond(tech1)
    t2_clause = get_cond(tech2)

    if output_format == "COUNT":
        sql = f"""
            SELECT COUNT(DISTINCT roll_number) AS student_count
            FROM ps_cleared_course_view
            WHERE status ILIKE 'Cleared'
              AND {t1_clause}
              AND roll_number NOT IN (
                  SELECT roll_number FROM ps_cleared_course_view
                  WHERE status ILIKE 'Cleared' AND {t2_clause}
              )
              {dept_filter}
        """
        metric = f"Students who cleared {tech1} but have NOT cleared {tech2}"
    else:
        sql = f"""
            SELECT roll_number, name,
                   substring(roll_number from '^[0-9]{{4}}[0-9]{{2}}[0-9]([A-Za-z]+)') AS dept_code,
                   string_agg(DISTINCT course_name, ', ' ORDER BY course_name) AS cleared_courses
            FROM ps_cleared_course_view
            WHERE status ILIKE 'Cleared'
              AND {t1_clause}
              AND roll_number NOT IN (
                  SELECT roll_number FROM ps_cleared_course_view
                  WHERE status ILIKE 'Cleared' AND {t2_clause}
              )
              {dept_filter}
            GROUP BY roll_number, name
            ORDER BY roll_number ASC
            LIMIT {min(limit, 2000)}
        """
        metric = f"Students who cleared {tech1} but have NOT cleared {tech2}"
    return validate_sql(sql), metric

# ==============================================================================
# LLM SQL GENERATION (FALLBACK)
# ==============================================================================

def generate_llm_sql(query: str, context: Dict[str, Any]) -> str:
    """Uses Groq to generate SQL for complex natural language queries with schema constraints."""
    system_prompt = f"""
You are a PostgreSQL expert for the SkillQuery academic analytics bot.
Output ONLY raw executable PostgreSQL query with NO markdown fences and NO preamble.

{SCHEMA_PROMPT}

TAXONOMY REFERENCE:
{get_taxonomy_summary()}

CRITICAL RULES:
- For student counts, ALWAYS use: SELECT COUNT(DISTINCT roll_number) AS student_count ...
- For completed students, filter: WHERE status ILIKE 'Cleared'
- For negative non-completion, use NOT EXISTS against status ILIKE 'Cleared'.
- Never invent column or table names. Only use ps_cleared_course_view.
- Always add LIMIT 50 for list queries.
"""
    response = groq_client.chat.completions.create(
        model=MODEL,
        temperature=0,
        max_tokens=400,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"User question: {query}\nContext: {json.dumps(context)}"}
        ]
    )
    raw = response.choices[0].message.content or ""
    return validate_sql(raw)

# ==============================================================================
# RESULT SYNTHESIZER
# ==============================================================================

def synthesize_answer(
    question: str, 
    cols: List[str], 
    rows: List[tuple], 
    meta: Dict[str, Any]
) -> str:
    """Creates a concise 2-line user answer using result data."""
    if not rows:
        target_name = meta.get("category_name") or "the requested criteria"
        return f"No matching student records found for **{target_name}**.\n*Based on verified database records.*"

    # Single-value count result
    if len(cols) == 1 and ("count" in cols[0].lower() or "students" in cols[0].lower()):
        count_val = rows[0][0]
        category_name = meta.get("category_name") or "the criteria"
        dept_name = meta.get("department_name")
        scope = f"in **{category_name}**" if category_name else ""
        if dept_name:
            scope += f" from **{dept_name}**"

        intent = meta.get("intent", "COMPLETED")
        if intent == "NOT_COMPLETED":
            line1 = f"**{count_val:,} students** have **not completed** courses {scope}."
        elif intent == "ATTEMPTED_NOT_CLEARED":
            line1 = f"**{count_val:,} students** attempted but **failed to clear** courses {scope}."
        elif intent == "PENDING":
            line1 = f"**{count_val:,} students** have **pending assessments** {scope}."
        elif intent == "PARTIAL":
            line1 = f"**{count_val:,} students** have **partially completed** courses {scope}."
        elif intent == "COMPARISON":
            line1 = f"**{count_val:,} students** cleared the first requirement but not the second."
        else:
            line1 = f"**{count_val:,} students** have cleared courses {scope}."

        desc = meta.get("description") or meta.get("metric") or "Based on verified assessment records."
        line2 = f"*{desc}*"
        return f"{line1}\n{line2}"

    # Table / Ranked list result
    count_val = len(rows)
    total_val = meta.get("total_matching_students", count_val)
    category_name = meta.get("category_name") or "the requested criteria"
    dept_name = meta.get("department_name")
    scope = f" from **{dept_name}**" if dept_name else ""
    intent = meta.get("intent", "COMPLETED")
    output_fmt = meta.get("output_format", "LIST")

    if output_fmt == "RANK":
        line1 = f"Showing **top {count_val} students** in **{category_name}**{scope}."
    elif intent == "NOT_COMPLETED":
        if total_val > 50:
            line1 = f"Showing **1-50 of {total_val:,} students** who have **not completed** **{category_name}**{scope}."
        else:
            line1 = f"Showing **all {total_val:,} students** who have **not completed** **{category_name}**{scope}."
    elif intent == "ATTEMPTED_NOT_CLEARED":
        if total_val > 50:
            line1 = f"Showing **1-50 of {total_val:,} students** who **attempted but did not clear** **{category_name}**{scope}."
        else:
            line1 = f"Showing **all {total_val:,} students** who **attempted but did not clear** **{category_name}**{scope}."
    elif intent == "PENDING":
        if total_val > 50:
            line1 = f"Showing **1-50 of {total_val:,} pending assessments** for **{category_name}**{scope}."
        else:
            line1 = f"Showing **all {total_val:,} pending assessments** for **{category_name}**{scope}."
    elif intent == "PARTIAL":
        if total_val > 50:
            line1 = f"Showing **1-50 of {total_val:,} students** who **partially completed** **{category_name}**{scope}."
        else:
            line1 = f"Showing **all {total_val:,} students** who **partially completed** **{category_name}**{scope}."
    else:
        if total_val > 50:
            line1 = f"Showing **1-50 of {total_val:,} matching students** for **{category_name}**{scope}."
        else:
            line1 = f"Showing **all {total_val:,} matching students** for **{category_name}**{scope}."

    metric = meta.get("metric") or "Based on verified assessment records."
    line2 = f"*{metric}*"
    return f"{line1}\n{line2}"

# ==============================================================================
# MAIN ENGINE PIPELINE
# ==============================================================================

def process_query(session_id: str, question: str) -> Dict[str, Any]:
    """Primary natural language query processing pipeline."""
    t0 = time.time()
    clean_q = question.strip()
    session = session_manager.get_session(session_id)
    ctx = session["current_context"]

    # 1. Parse Intents
    completion_intent = detect_completion_intent(clean_q)
    output_format = detect_output_format(clean_q)
    cat_match = resolve_category(clean_q)
    dept_match = resolve_department(clean_q)
    comparison = extract_comparison_targets(clean_q)
    course_entities = extract_course_entities(clean_q)
    course_level = extract_course_level(clean_q)

    # 2. Check Pronoun & Follow-up Resolution
    has_pronoun = bool(re.search(r"\b(it|them|those|that|same)\b", clean_q.lower()))
    is_clarification = bool(re.search(r"^(i mean|meaning|students who)\b", clean_q.lower()))
    is_follow_up_filter = bool(re.search(r"^(what about|and for|how about|what of)\b", clean_q.lower()))
    is_follow_up_list = bool(re.search(r"\b(show (their )?names|who are they|list them|show them|give me their names)\b", clean_q.lower()))

    is_follow_up = has_pronoun or is_clarification or is_follow_up_filter or is_follow_up_list

    # Context resolution rules:
    # If the user asks a follow-up, inherit category/entities and department
    if is_follow_up and not cat_match and not course_entities and not comparison:
        if ctx.get("category"):
            cat_match = TAXONOMY.get(ctx["category"])
        elif ctx.get("entities"):
            course_entities = ctx["entities"]
        dept_code = dept_match["code"] if dept_match else ctx.get("department")
    elif is_follow_up_filter and not cat_match:
        # e.g. "What about CSE?" keeps active category
        if ctx.get("category"):
            cat_match = TAXONOMY.get(ctx["category"])
        elif ctx.get("entities"):
            course_entities = ctx["entities"]
        dept_code = dept_match["code"] if dept_match else ctx.get("department")
    else:
        # A new independent question sets department only if specified in THIS question
        dept_code = dept_match["code"] if dept_match else None

    # 3. Route Query to Target Builder
    # Case A: Comparison (e.g. Python but not Java)
    if comparison:
        t1, t2 = comparison
        sql, metric = build_comparison_sql(t1, t2, output_format, dept_code)
        meta = {
            "intent": "COMPARISON",
            "category_name": f"{t1} but not {t2}",
            "metric": metric,
            "department": dept_code,
            "department_name": dept_match["name"] if dept_match else None
        }
        session_manager.update_context(session_id, {
            "entities": [t1, t2],
            "category": None,
            "department": dept_code,
            "intent": "COMPARISON"
        })

    # Case B: Specific Course(s) Query (C, C Programming, Python, Java, SQL, DSA, HTML/CSS, React, etc.)
    # Specific courses take precedence over broad categories
    elif course_entities:
        limit = 10 if output_format == "RANK" else 2000
        sql, metric = build_single_or_multi_course_sql(
            course_entities, completion_intent, output_format, dept_code, level=course_level, limit=limit
        )
        display_course_name = " & ".join(course_entities)
        if course_level:
            display_course_name += f" Level {course_level.upper()}"
        cat_key = None
        if len(course_entities) == 1 and course_entities[0] in CANONICAL_COURSES:
            cat_key = CANONICAL_COURSES[course_entities[0]].get("category")
        elif cat_match:
            cat_key = cat_match["key"]

        meta = {
            "intent": completion_intent,
            "entities": course_entities,
            "category": cat_key,
            "category_name": display_course_name,
            "level": course_level,
            "metric": metric,
            "department": dept_code,
            "department_name": dept_match["name"] if dept_match else None
        }
        session_manager.update_context(session_id, {
            "entities": course_entities,
            "category": cat_key,
            "department": dept_code,
            "department_name": dept_match["name"] if dept_match else None,
            "intent": completion_intent,
            "level": course_level
        })

    # Case C: Category Query (Frontend, Backend, Database Management, DSA, OS, etc.)
    elif cat_match:
        cat_key = cat_match["key"]
        limit = 10 if output_format == "RANK" else 2000
        sql, metric = build_category_sql(
            cat_key, completion_intent, output_format, dept_code, level=course_level, limit=limit
        )
        display_cat_name = cat_match["display_name"]
        if course_level:
            display_cat_name += f" Level {course_level.upper()}"
        meta = {
            "intent": completion_intent,
            "category": cat_key,
            "category_name": display_cat_name,
            "description": cat_match["description"],
            "level": course_level,
            "metric": metric,
            "department": dept_code,
            "department_name": dept_match["name"] if dept_match else None
        }
        session_manager.update_context(session_id, {
            "category": cat_key,
            "category_name": cat_match["display_name"],
            "department": dept_code,
            "department_name": dept_match["name"] if dept_match else None,
            "intent": completion_intent,
            "level": course_level,
            "entities": []
        })

    # Case D: Ad-Hoc LLM Query
    else:
        sql = generate_llm_sql(clean_q, ctx)
        meta = {
            "intent": completion_intent,
            "department": dept_code,
            "department_name": dept_match["name"] if dept_match else None,
            "metric": "Generated SQL query"
        }
        session_manager.update_context(session_id, {
            "department": dept_code,
            "intent": completion_intent
        })

    # Execute Guarded SQL
    meta["sql"] = sql
    meta["output_format"] = output_format
    cols, raw_rows = fetch_rows(sql)

    total_count = len(raw_rows)
    meta["total_matching_students"] = total_count
    meta["result_count"] = total_count
    meta["page_size"] = 50
    meta["total_pages"] = (total_count + 49) // 50 if total_count > 0 else 1

    dict_rows = [
        dict(zip(cols, [str(v) if v is not None else None for v in row]))
        for row in raw_rows
    ]

    # Decorate department name if dept_code in columns
    if "dept_code" in cols:
        for r in dict_rows:
            d_code = r.get("dept_code")
            if d_code and d_code in DEPARTMENTS:
                r["department"] = f"{DEPARTMENTS[d_code]['name']} ({d_code})"

    final_cols = list(cols)
    if "dept_code" in final_cols and "department" not in final_cols:
        idx = final_cols.index("dept_code")
        final_cols.insert(idx + 1, "department")

    answer = synthesize_answer(clean_q, cols, raw_rows, meta)
    latency_ms = int((time.time() - t0) * 1000)
    meta["latency_ms"] = latency_ms

    session_manager.add_turn(session_id, clean_q, answer, sql)
    session_manager.update_context(session_id, {"last_sql": sql, "last_answer": answer})

    return {
        "answer": answer,
        "columns": final_cols,
        "rows": dict_rows,
        "meta": meta
    }
