import os
import json
import logging
from pathlib import Path
from fastapi import FastAPI, Request, HTTPException
from fastapi.responses import FileResponse, PlainTextResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import httpx
from dotenv import load_dotenv

from query_engine import process_query
from session_memory import session_manager
from course_taxonomy import TAXONOMY

load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("skillquery")

app = FastAPI(
    title="SkillQuery - Student Skills Intelligence Assistant",
    description="Natural-language querying and course taxonomy analytics for student records."
)

FRONTEND_DIR = Path(__file__).parent / "frontend"
app.mount("/frontend", StaticFiles(directory=FRONTEND_DIR), name="frontend")

VERIFY_TOKEN = os.getenv("WHATSAPP_VERIFY_TOKEN", "")
WA_TOKEN = os.getenv("WHATSAPP_ACCESS_TOKEN", "")
PHONE_ID = os.getenv("WHATSAPP_PHONE_NUMBER_ID", "")
GRAPH_VERSION = os.getenv("META_GRAPH_VERSION", "v22.0")

class QueryRequest(BaseModel):
    question: str
    session_id: str

class ResetRequest(BaseModel):
    session_id: str

@app.get("/")
def frontend():
    return FileResponse(FRONTEND_DIR / "index.html")

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "SkillQuery Assistant",
        "taxonomy_categories": list(TAXONOMY.keys())
    }

@app.get("/api/taxonomy")
def get_taxonomy():
    """Returns the course taxonomy categories and descriptions."""
    return {
        k: {
            "name": v["display_name"],
            "description": v["description"],
            "courses": v["courses"]
        }
        for k, v in TAXONOMY.items()
    }

@app.post("/api/query")
def query_endpoint(request: QueryRequest):
    question = request.question.strip()
    session_id = request.session_id.strip()

    if not question:
        raise HTTPException(status_code=400, detail="Question cannot be empty.")
    if not session_id:
        raise HTTPException(status_code=400, detail="Session ID is required.")

    logger.info("Query received | session=%s | question=%s", session_id, question)

    try:
        result = process_query(session_id, question)
        logger.info(
            "Query processed | session=%s | latency=%sms | results=%s",
            session_id,
            result.get("meta", {}).get("latency_ms"),
            result.get("meta", {}).get("result_count")
        )
        return result
    except Exception as error:
        logger.error("Query failed | session=%s | error=%s", session_id, error, exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Query failed: {str(error)}"
        ) from error

@app.post("/api/reset")
def reset_session(request: ResetRequest):
    session_id = request.session_id.strip()
    if session_id:
        session_manager.clear_session(session_id)
        logger.info("Session cleared | session=%s", session_id)
    return {"status": "cleared", "session_id": session_id}

# ==============================================================================
# WHATSAPP INTEGRATION
# ==============================================================================

async def send_whatsapp(to: str, body: str):
    if not (WA_TOKEN and PHONE_ID):
        logger.warning("WhatsApp credentials missing; skipping outbound message.")
        return
    url = f"https://graph.facebook.com/{GRAPH_VERSION}/{PHONE_ID}/messages"
    payload = {
        "messaging_product": "whatsapp",
        "recipient_type": "individual",
        "to": to,
        "type": "text",
        "text": {"preview_url": False, "body": body[:4000]}
    }
    async with httpx.AsyncClient(timeout=20) as client:
        r = await client.post(url, headers={"Authorization": f"Bearer {WA_TOKEN}"}, json=payload)
        r.raise_for_status()

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
            result = process_query(sender, text_body)
            answer = result["answer"]
        except Exception as e:
            logger.error("WhatsApp handling failed: %s", e)
            answer = "I couldn't process that query. Please try asking again."

        await send_whatsapp(sender, answer)
    except Exception as e:
        logger.error("Webhook processing failed: %s", e)
    return {"status": "received"}
