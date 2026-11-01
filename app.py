import os, json
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import PlainTextResponse
import httpx
from groq import Groq
from dotenv import load_dotenv
from db import fetch_rows
from sql_guard import validate_sql

load_dotenv()
app = FastAPI(title="Student Skills WhatsApp Query Bot")
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")
VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
WA_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
PHONE_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v22.0")

SCHEMA = """
Approved PostgreSQL table: ps_cleared_course_view
Columns:
roll_number VARCHAR, name VARCHAR, vertical_name VARCHAR, course_name VARCHAR,
date DATE, start_time TIME, end_time TIME, venue_name VARCHAR, status VARCHAR.
status examples: Cleared, Not Cleared, Pending for Result.
Each row is an assessment/course attempt, not necessarily a unique skill.
Use COUNT(DISTINCT roll_number) for number of students.
Use COUNT(*) only when asking number of records/attempts.
Use case-insensitive matching with ILIKE.
For a student's latest result per course, use DISTINCT ON or a window function
ordered by date DESC; do not assume every duplicate attempt is the latest.
Do not invent columns such as department, GPA, placement status, or skills.
'Full stack' and 'backend' are not explicit columns; search course/vertical names
for relevant terms and explain that results are based on matching names.
Only SELECT queries. Always include LIMIT <= 100 for row results.
"""

def generate_sql(question: str) -> str:
    response = groq_client.chat.completions.create(
        model=MODEL,
        temperature=0,
        max_tokens=700,
        messages=[
            {"role": "system", "content":
             "Translate the user's question into ONE safe PostgreSQL SELECT query. "
             "Return SQL only, no markdown. Use only the table and columns below. "
             "Never expose credentials or query other tables. For ranking students, "
             "group by roll_number and name, count distinct relevant cleared course "
             "names as appropriate, and order descending. Never infer actual skills "
             "not represented by course/vertical names. Use LIMIT 10 for top 10. "
             "Do not return individual student data unless the question asks for it. "
             "Schema and semantics:\n" + SCHEMA},
            {"role": "user", "content": question}
        ],
    )
    return validate_sql(response.choices[0].message.content or "")

def answer_question(question: str) -> str:
    sql = generate_sql(question)
    cols, rows = fetch_rows(sql)
    if not rows:
        return "No matching records found. Try a broader course or skill keyword."
    result = [dict(zip(cols, [str(v) if v is not None else None for v in row])) for row in rows]
    # Summarize only the returned database results; don't let the model run another query.
    response = groq_client.chat.completions.create(
        model=MODEL, temperature=0.2, max_tokens=700,
        messages=[
            {"role": "system", "content":
             "Answer clearly and briefly using ONLY the database result supplied. "
             "Do not add facts or names that are not in the result. Mention if the "
             "query is based on matching course/vertical names rather than an explicit skill field."},
            {"role": "user", "content":
             f"Question: {question}\nSQL used: {sql}\nDatabase rows (JSON): {json.dumps(result, ensure_ascii=False)}"}
        ],
    )
    return response.choices[0].message.content or str(result)

async def send_whatsapp(to: str, body: str):
    if not (WA_TOKEN and PHONE_ID):
        raise RuntimeError("WhatsApp Cloud API credentials are missing")
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{PHONE_ID}/messages"
    payload = {
        "messaging_product": "whatsapp", "recipient_type": "individual",
        "to": to, "type": "text", "text": {"preview_url": False, "body": body[:4000]}
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, headers={"Authorization": f"Bearer {WA_TOKEN}"}, json=payload)
        r.raise_for_status()

@app.get("/")
def health():
    return {"status": "ok", "service": "Student Skills WhatsApp Query Bot"}

@app.get("/webhook")
def verify_webhook(request: Request):
    # FastAPI's Request query_params are synchronous properties.
    mode = request.query_params.get("hub.mode")
    token = request.query_params.get("hub.verify_token")
    challenge = request.query_params.get("hub.challenge")
    if mode == "subscribe" and token and token == VERIFY_TOKEN and challenge:
        return PlainTextResponse(challenge)
    raise HTTPException(status_code=403, detail="Webhook verification failed")

@app.post("/webhook")
async def receive_webhook(request: Request):
    body = await request.json()
    # Meta can send status updates without an incoming message.
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
            answer = answer_question(text_body)
        except Exception as e:
            # Do not send database internals or secrets to the user.
            print(f"Question handling failed: {type(e).__name__}: {e}")
            answer = "I couldn't process that query. Please rephrase it or contact the bot administrator."
        await send_whatsapp(sender, answer)
    except Exception as e:
        print(f"Webhook processing failed: {type(e).__name__}: {e}")
    return {"status": "received"}
