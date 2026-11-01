import os, json, re
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx
from groq import Groq
from dotenv import load_dotenv
from db import fetch_rows
from sql_guard import validate_sql

load_dotenv()
app = FastAPI(title="Student Skills WhatsApp Query Bot")
FRONTEND_DIR = Path(__file__).parent / "frontend"
app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
WA_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
PHONE_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v22.0")

# Session store to track multi-step options per user
USER_SESSIONS = {}

STOP_WORDS = {
    "how", "many", "distinct", "students", "student", "cleared", "clear", "passed", "pass",
    "have", "has", "count", "number", "of", "who", "show", "total", "list", "the", "for",
    "in", "what", "is", "are", "which", "give", "me", "tell", "get", "result", "results",
    "course", "courses", "vertical", "verticals", "attempt", "attempts",
    "top", "first", "latest", "most"
}

SCHEMA = """
Approved PostgreSQL table: ps_cleared_course_view
Columns:
roll_number VARCHAR, name VARCHAR, vertical_name VARCHAR, course_name VARCHAR,
date DATE, start_time TIME, end_time TIME, venue_name VARCHAR, status VARCHAR.

QUERYING RULES:
1. Each row represents an assessment/course attempt.
2. Use COUNT(DISTINCT roll_number) for student counts.
3. Use COUNT(*) only for record/attempt counts.
4. Always filter status ILIKE 'Cleared' when user asks for cleared/passed students.
5. Only SELECT queries. Always include LIMIT <= 100 for row results.
"""

def normalize_str(text: str) -> str:
    """Removes non-alphanumeric characters and converts to lowercase for comparisons."""
    return re.sub(r'[^a-zA-Z0-9]', '', str(text)).lower()

def stem_term(term: str) -> str:
    """Strips plural suffixes ('s' or 'es') so singular/plural search terms match."""
    t = term.strip()
    if t.lower().endswith('es') and len(t) > 4:
        return t[:-2]
    if t.lower().endswith('s') and len(t) > 3 and not t.lower().endswith('ss'):
        return t[:-1]
    return t

def extract_entity_phrases(question: str) -> list[str]:
    """Extracts complete database entity phrases, preserving AND/OR groups."""
    prompt = (
        "Extract every distinct database entity phrase requested by the user as "
        "a JSON array. Preserve words, punctuation, and numeric designations "
        "that belong together. Separate entities joined by conjunctions. Do not "
        "invent or normalize entity names. Return JSON only.\n"
        f"Question: {question}"
    )
    try:
        response = groq_client.chat.completions.create(
            model=MODEL,
            temperature=0,
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        match = re.search(r"\[.*\]", response.choices[0].message.content or "", re.DOTALL)
        phrases = json.loads(match.group(0)) if match else []
        if isinstance(phrases, list):
            cleaned = split_entity_phrases(phrases)
            if cleaned:
                return list(dict.fromkeys(cleaned))
    except Exception as error:
        print(f"Entity extraction failed: {type(error).__name__}: {error}")

    question = re.sub(
        r"\b(how many|count|number of|distinct|students?|who|cleared|passed|"
        r"show|list|what is|what are|give me|tell me|the|all)\b",
        " ",
        question,
        flags=re.I,
    )
    phrases = re.split(r"\s+(?:and|or)\s+", question, flags=re.I)
    return [
        phrase
        for phrase in split_entity_phrases(phrases)
        if phrase
    ]

def split_entity_phrases(phrases: list) -> list[str]:
    """Splits conjunction-joined entities returned by the extractor."""
    result = []
    for phrase in phrases:
        parts = re.split(r"\s+(?:and|or)\s+", str(phrase), flags=re.I)
        result.extend(clean_entity_phrase(part) for part in parts)
    return [phrase for phrase in result if phrase]

def clean_entity_phrase(phrase: str) -> str:
    """Removes generic query language while preserving entity words and levels."""
    cleaned = re.sub(r"\s+", " ", phrase).strip(" ?,.")
    cleaned = re.sub(r"^(?:top|first|latest|most)\s+\d+\s+", "", cleaned, flags=re.I)
    while True:
        updated = re.sub(
            r"^(?:(?:top|first|latest|most)\s+\d+|how|many|distinct|student|students|cleared|clear|passed|pass|"
            r"have|has|count|number|of|who|show|total|list|the|for|in|what|is|"
            r"are|which|give|me|tell|get|result|results|course|courses|vertical|"
            r"verticals|attempt|attempts|top|first|latest|most)\s+",
            "",
            cleaned,
            flags=re.I,
        )
        if updated == cleaned:
            return cleaned
        cleaned = updated

def resolve_vertical_or_course(question: str) -> dict:
    """Resolves every requested entity independently before SQL generation."""
    phrases = extract_entity_phrases(question)
    if not phrases:
        return {"status": "proceed", "resolved_term": None}

    resolved = []
    unresolved = []
    ambiguous_groups = []
    for phrase in phrases:
        terms = [
            normalize_str(stem_term(term))
            for term in re.findall(r"[a-zA-Z0-9]+", phrase)
            if term.lower() not in STOP_WORDS
        ]
        if not terms:
            continue
        conditions = " AND ".join(
            "(regexp_replace(LOWER(vertical_name), '[^a-z0-9]', '', 'g') LIKE %s "
            "OR regexp_replace(LOWER(course_name), '[^a-z0-9]', '', 'g') LIKE %s)"
            for _ in terms
        )
        params = [value for term in terms for value in (f"%{term}%", f"%{term}%")]
        try:
            _, rows = fetch_rows(
                f"SELECT DISTINCT vertical_name, course_name FROM ps_cleared_course_view "
                f"WHERE {conditions} LIMIT 100",
                tuple(params),
            )
        except Exception as error:
            print(f"Entity lookup failed: {type(error).__name__}: {error}")
            rows = []
        matches = sorted({
            value for vertical, course in rows
            for value in (vertical, course)
            if value and all(term in normalize_str(value) for term in terms)
        })
        if len(matches) == 1:
            resolved.append(matches[0])
        elif len(matches) > 1:
            ambiguous_groups.append(matches)
        else:
            unresolved.append(phrase)

    if ambiguous_groups:
        return {
            "status": "ambiguous",
            "options": ambiguous_groups[0],
            "pending_options": ambiguous_groups[1:],
            "resolved_entities": resolved,
        }
    if unresolved:
        return {"status": "unresolved", "phrases": unresolved}
    return {"status": "proceed", "resolved_term": resolved}

def get_sub_levels(entity_name: str) -> list[str]:
    """Queries DB to find all distinct course levels or sub-courses under a topic."""
    sql = """
        SELECT DISTINCT course_name
        FROM ps_cleared_course_view
        WHERE vertical_name ILIKE %s OR course_name ILIKE %s
        ORDER BY course_name;
    """
    param = f"%{entity_name}%"
    try:
        cols, rows = fetch_rows(sql, (param, param))
        if not rows:
            return []
        return sorted(list({r[0] for r in rows if r[0]}))
    except Exception as e:
        print(f"Error fetching sub-levels: {e}")
        return []

def format_selection_message(message: str, options: list[str]) -> str:
    lines = [message, "", "Please select an option:"]
    lines.extend(f"*{idx}* - {option}" for idx, option in enumerate(options, 1))
    return "\n".join(lines)

def execute_multi_entity_query(
    question: str, entities: list[str], structured: bool = False
) -> str | dict:
    entity_filter = " OR ".join(
        "(vertical_name ILIKE %s OR course_name ILIKE %s)" for _ in entities
    )
    entity_count = "COUNT(DISTINCT CASE " + " ".join(
        "WHEN (vertical_name ILIKE %s OR course_name ILIKE %s) THEN %s"
        for _ in entities
    ) + " END)"
    filter_params = [
        value for entity in entities
        for value in (f"%{entity}%", f"%{entity}%")
    ]
    count_params = [
        value
        for entity in entities
        for value in (f"%{entity}%", f"%{entity}%", entity)
    ]
    asks_for_count = bool(re.search(
        r"\b(count|counts|how many|number of|total)\b", question, re.I
    ))
    wants_rows = not asks_for_count and bool(re.search(
        r"\b(who|list|show|top|which)\b", question, re.I
    ))
    if wants_rows:
        sql = f"""
            SELECT roll_number, name, {entity_count} AS matched_entities
            FROM ps_cleared_course_view
            WHERE status ILIKE 'Cleared' AND ({entity_filter})
            GROUP BY roll_number, name
            HAVING {entity_count} = {len(entities)}
            ORDER BY matched_entities DESC, name
            LIMIT 100
        """
        params = count_params + filter_params + count_params
    else:
        sql = f"""
            SELECT COUNT(*) AS student_count
            FROM (
                SELECT roll_number
                FROM ps_cleared_course_view
                WHERE status ILIKE 'Cleared' AND ({entity_filter})
                GROUP BY roll_number
                HAVING {entity_count} = {len(entities)}
            ) matched_students
        """
        params = filter_params + count_params
    cols, rows = fetch_rows(sql, tuple(params))
    result = [dict(zip(cols, [str(value) if value is not None else None for value in row])) for row in rows]
    if not result:
        answer = "No students matched all selected entities."
        return {"answer": answer, "columns": [], "rows": []} if structured else answer
    response = groq_client.chat.completions.create(
        model=MODEL,
        temperature=0.2,
        max_tokens=300,
        messages=[
            {"role": "system", "content":
             "Answer using only the supplied database result. Return exactly two short lines. "
             "Bold the key result on line one and describe the selected entities on line two."},
            {"role": "user", "content": f"Question: {question}\nResult: {json.dumps(result)}"},
        ],
    )
    answer = response.choices[0].message.content or str(result)
    return {"answer": answer, "columns": cols, "rows": result} if structured else answer

def generate_sql(question: str, resolved_entity: str | list[str] = None) -> str:
    """Generates PostgreSQL query using the exact resolved vertical or course name."""
    if resolved_entity:
        entities = [resolved_entity] if isinstance(resolved_entity, str) else resolved_entity
        entity_text = json.dumps(entities, ensure_ascii=False)
        system_content = (
            "You are a PostgreSQL expert. Output ONLY the executable raw SQL query with no explanation or markdown fences.\n"
            f"The complete database entity targets are EXACTLY: {entity_text}.\n"
            "Every target must be included in the query. IMPORTANT: one assessment "
            "row cannot match two different entities. When there are multiple "
            "targets, first filter rows with status ILIKE 'Cleared' and one OR "
            "condition per target, then GROUP BY roll_number and name and use "
            "HAVING COUNT(DISTINCT CASE WHEN entity_condition_1 THEN 'entity_1' "
            "WHEN entity_condition_2 THEN 'entity_2' END) equal to "
            f"{len(entities)}. This finds students who cleared every target across separate "
            "rows. Never put different entity conditions in an AND clause on the "
            "same row. Do not use abbreviated wording or add entities not in the "
            "target list. Keep SQL to the approved table and columns.\n"
            "Use COUNT(DISTINCT roll_number) for student counts.\n"
            + SCHEMA
        )
    else:
        system_content = (
            "You are a PostgreSQL expert. Output ONLY the executable raw SQL query with no explanation or markdown fences.\n"
            "Split all search keywords into separate ILIKE conditions joined with AND.\n"
            + SCHEMA
        )

    response = groq_client.chat.completions.create(
        model=MODEL,
        temperature=0,
        max_tokens=700,
        messages=[
            {"role": "system", "content": system_content},
            {"role": "user", "content": question}
        ],
    )
    return validate_sql(response.choices[0].message.content or "")

def execute_and_answer(
    question: str, resolved_entity: str | list[str] = None, structured: bool = False
) -> str | dict:
    """Helper function to execute SQL and format the answer from Groq."""
    if isinstance(resolved_entity, list) and resolved_entity:
        return execute_multi_entity_query(question, resolved_entity, structured)
    sql = generate_sql(question, resolved_entity)
    cols, rows = fetch_rows(sql)

    if not rows:
        target_msg = f" for '{resolved_entity}'" if resolved_entity else ""
        answer = f"No matching records found{target_msg}. Try rephrasing your search keywords."
        return {"answer": answer, "columns": [], "rows": []} if structured else answer

    result = [dict(zip(cols, [str(v) if v is not None else None for v in row])) for row in rows]

    response = groq_client.chat.completions.create(
        model=MODEL, temperature=0.2, max_tokens=700,
        messages=[
            {"role": "system", "content":
             "Answer using ONLY the database result supplied. Return exactly two lines. "
             "Line 1 must be a short, crisp answer with the important result wrapped "
             "in markdown bold. Line 2 must be one "
             "short description explaining the matched course, vertical, or level. "
             "Do not add headings, bullets, greetings, or extra explanation."},
            {"role": "user", "content":
             f"Question: {question}\nTarget Entity: {resolved_entity}\nSQL used: {sql}\nDatabase rows (JSON): {json.dumps(result, ensure_ascii=False)}"}
        ],
    )
    answer = response.choices[0].message.content or str(result)
    if structured:
        return {"answer": answer, "columns": cols, "rows": result}
    return answer

def answer_question(sender: str, question: str, structured: bool = False) -> str | dict:
    global USER_SESSIONS
    clean_text = question.strip()
    norm_input = normalize_str(clean_text)

    # 1. PROCESS MULTI-STEP SESSION (Topic Selection -> Level Selection -> Execute)
    if sender in USER_SESSIONS:
        session = USER_SESSIONS[sender]
        step = session.get("step", "SELECT_TOPIC")
        options = session.get("options", [])
        orig_question = session.get("original_question", question)

        selected_option = None

        # Check numeric selection (e.g., "1", "2")
        num_match = re.search(r"^\s*(?:option\s*)?(\d+)\s*$", clean_text, re.I)
        if num_match:
            idx = int(num_match.group(1)) - 1
            if 0 <= idx < len(options):
                selected_option = options[idx]

        # Check text matching selection
        if not selected_option:
            for opt in options:
                if norm_input == normalize_str(opt):
                    selected_option = opt
                    break

        if selected_option:
            # STEP 1: TOPIC SELECTED -> CHECK FOR SUB-LEVELS
            if step == "SELECT_TOPIC":
                pending_options = session.get("pending_options", [])
                if pending_options:
                    USER_SESSIONS[sender] = {
                        "step": "SELECT_TOPIC",
                        "options": pending_options[0],
                        "pending_options": pending_options[1:],
                        "multi_entity": True,
                        "resolved_entities": [
                            *session.get("resolved_entities", []),
                            selected_option,
                        ],
                        "original_question": orig_question,
                    }
                    return format_selection_message(
                        "Now select the matching option for the next requested entity.",
                        pending_options[0],
                    )
                if session.get("multi_entity"):
                    del USER_SESSIONS[sender]
                    targets = list(dict.fromkeys([
                        *session.get("resolved_entities", []),
                        selected_option,
                    ]))
                    return execute_and_answer(orig_question, targets, structured)

                sub_courses = get_sub_levels(selected_option)

                # Find sub-courses/levels distinct from the topic itself
                distinct_levels = [
                    c for c in sub_courses
                    if normalize_str(c) != normalize_str(selected_option)
                ]

                if len(distinct_levels) >= 1:
                    level_options = ["All Levels (Overall Count)"] + sub_courses
                    level_options = list(dict.fromkeys(level_options))

                    USER_SESSIONS[sender] = {
                        "step": "SELECT_LEVEL",
                        "selected_topic": selected_option,
                        "options": level_options,
                        "resolved_entities": session.get("resolved_entities", []),
                        "original_question": orig_question
                    }

                    msg = f"Which level of *{selected_option}* are you referring to?\n\n"
                    for idx, opt in enumerate(level_options, 1):
                        msg += f"*{idx}* - {opt}\n"
                    return msg

                # No sub-levels exist -> execute query directly for selected topic
                del USER_SESSIONS[sender]
                entities = session.get("resolved_entities", [])
                targets = list(dict.fromkeys([*entities, selected_option]))
                return execute_and_answer(orig_question, targets, structured)

            # STEP 2: LEVEL SELECTED -> EXECUTE FINAL QUERY
            elif step == "SELECT_LEVEL":
                selected_topic = session.get("selected_topic", selected_option)
                del USER_SESSIONS[sender]

                if "all levels" in selected_option.lower():
                    selected_target = selected_topic
                else:
                    selected_target = selected_option
                entities = session.get("resolved_entities", [])
                targets = list(dict.fromkeys([*entities, selected_target]))
                return execute_and_answer(orig_question, targets, structured)

        del USER_SESSIONS[sender]

    # 2. PROCESS NEW QUESTION
    resolution = resolve_vertical_or_course(question)
    
    if resolution["status"] == "ambiguous":
        options = resolution["options"]
        USER_SESSIONS[sender] = {
            "step": "SELECT_TOPIC",
            "options": options,
            "pending_options": resolution.get("pending_options", []),
            "multi_entity": bool(resolution.get("pending_options")),
            "resolved_entities": resolution.get("resolved_entities", []),
            "original_question": question
        }
        
        return format_selection_message(
            "Multiple matching topics/verticals were found.",
            options,
        )

    if resolution["status"] == "unresolved":
        phrases = ", ".join(resolution["phrases"])
        message = f"I could not uniquely match: {phrases}. Please provide the complete course or vertical name."
        return {"answer": message, "columns": [], "rows": []} if structured else message

    resolved_entity = resolution.get("resolved_term")
    return execute_and_answer(question, resolved_entity, structured)

async def send_whatsapp(to: str, body: str):
    if not (WA_TOKEN and PHONE_ID):
        raise RuntimeError("WhatsApp Cloud API credentials missing")
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{PHONE_ID}/messages"
    payload = {
        "messaging_product": "whatsapp", "recipient_type": "individual",
        "to": to, "type": "text", "text": {"preview_url": False, "body": body[:4000]}
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, headers={"Authorization": f"Bearer {WA_TOKEN}"}, json=payload)
        r.raise_for_status()

class QueryRequest(BaseModel):
    question: str
    session_id: str


@app.get("/")
def frontend():
    return FileResponse(FRONTEND_DIR / "index.html")


@app.get("/health")
def health():
    return {"status": "ok", "service": "Student Skills WhatsApp Query Bot"}


@app.post("/api/query")
def query(request: QueryRequest):
    question = request.question.strip()
    session_id = request.session_id.strip()
    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID is required.")
    try:
        result = answer_question(session_id, question, structured=True)
        if isinstance(result, dict):
            return result
        return {"answer": result, "columns": [], "rows": []}
    except Exception as error:
        print(f"Frontend query failed: {type(error).__name__}: {error}")
        raise HTTPException(
            status_code=500,
            detail="The question could not be processed. Please try again.",
        ) from error

@app.get("/webhook")
def verify_webhook(request: Request):
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token and token == VERIFY_TOKEN and challenge:
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="Webhook verification failed")

@app.post("/webhook")
async def receive_webhook(request: Request):
    body = await request.json()
    try:
        value = body["entry"][0]["changes"][0]["value"]
        messages = value.get("messages", [])
        if not messages:
            return {"status": "ignored"}
        msg = messages[0]
        sender = msg.get("from")
        text_body = msg.get("text", {}).get("body", "").strip()
        if not sender or not text_body:
            return {"status": "ignored"}
        try:
            answer = answer_question(sender, text_body)
        except Exception as e:
            print(f"Question handling failed: {type(e).__name__}: {e}")
            answer = "I couldn't process that query. Please try asking again."
        await send_whatsapp(sender, answer)
    except Exception as e:
        print(f"Webhook processing failed: {type(e).__name__}: {e}")
    return {"status": "received"}