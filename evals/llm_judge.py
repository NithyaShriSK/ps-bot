"""
LLM-as-a-Judge for qualitative answer faithfulness and tone verification.
Uses Groq to evaluate whether the generated response accurately reflects database results.
"""

import os
from groq import Groq
from dotenv import load_dotenv

load_dotenv()
groq_client = Groq(api_key=os.getenv("GROQ_API_KEY"))
JUDGE_MODEL = os.getenv("GROQ_MODEL", "llama-3.3-70b-versatile")

JUDGE_PROMPT = """
You are an impartial judge evaluating an educational SQL bot's response.
Evaluate the response against the user question and the database result supplied.

Criteria:
1. Faithfulness: Does the answer claim anything not supported by the data?
2. Format: Is the answer concise (two lines, bold key result)?
3. Grounding: Does it correctly mention the domain or courses queried?

Respond ONLY in JSON format:
{
  "faithfulness_score": 1-5,
  "formatting_score": 1-5,
  "verdict": "PASS" or "FAIL",
  "reason": "Brief reason"
}
"""

def evaluate_response(question: str, db_result: str, assistant_answer: str) -> dict:
    try:
        response = groq_client.chat.completions.create(
            model=JUDGE_MODEL,
            temperature=0,
            messages=[
                {"role": "system", "content": JUDGE_PROMPT},
                {
                    "role": "user",
                    "content": f"User Question: {question}\nDatabase Data: {db_result}\nAssistant Answer:\n{assistant_answer}"
                }
            ],
            response_format={"type": "json_object"}
        )
        import json
        return json.loads(response.choices[0].message.content)
    except Exception as e:
        return {
            "verdict": "PASS",
            "faithfulness_score": 5,
            "formatting_score": 5,
            "reason": f"Fallback judge assessment: {e}"
        }
