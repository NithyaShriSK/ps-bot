"""
Conversational Session Memory for SkillQuery.
Tracks context, resolved categories, entities, filters, and SQL across turns.
"""

import time
from typing import Dict, Any, Optional

SESSION_TTL_SECONDS = 3600  # 1 hour session expiry

class SessionMemory:
    def __init__(self):
        self._sessions: Dict[str, Dict[str, Any]] = {}

    def get_session(self, session_id: str) -> Dict[str, Any]:
        """Retrieves or creates a session context."""
        now = time.time()
        if session_id in self._sessions:
            session = self._sessions[session_id]
            # Check expiration
            if now - session.get("last_active", 0) > SESSION_TTL_SECONDS:
                self.clear_session(session_id)
            else:
                session["last_active"] = now
                return session

        new_session = {
            "session_id": session_id,
            "created_at": now,
            "last_active": now,
            "history": [],
            "current_context": {
                "category": None,
                "category_name": None,
                "department": None,
                "department_name": None,
                "entities": [],
                "intent": None,
                "last_sql": None,
                "last_answer": None
            }
        }
        self._sessions[session_id] = new_session
        return new_session

    def update_context(self, session_id: str, updates: Dict[str, Any]):
        """Updates the current contextual state for follow-up questions."""
        session = self.get_session(session_id)
        ctx = session["current_context"]
        for k, v in updates.items():
            if v is not None:
                ctx[k] = v
        session["last_active"] = time.time()

    def add_turn(self, session_id: str, question: str, answer: str, sql: Optional[str] = None):
        """Appends a turn to conversation history."""
        session = self.get_session(session_id)
        session["history"].append({
            "timestamp": time.time(),
            "question": question,
            "answer": answer,
            "sql": sql
        })
        # Keep last 10 turns
        if len(session["history"]) > 10:
            session["history"] = session["history"][-10:]

    def clear_session(self, session_id: str):
        """Clears session memory."""
        if session_id in self._sessions:
            del self._sessions[session_id]

# Singleton session manager
session_manager = SessionMemory()
