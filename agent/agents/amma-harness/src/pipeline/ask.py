"""Ask about Amma: a family member's free-text question, answered from her record, checked by the policy live.

One model drafts (fast Gemini, answering directly); a different model guards (Claude, summarize-never-treat).
The policy sees the question, so a bare "No" to "Should we reduce her dose?" is judged as the advice it is.
"""

import json
import os
from datetime import datetime, timezone

from google import genai
from pymongo.database import Database

from pipeline import policy, visitprep

DRAFTER_MODEL = os.environ.get("ASK_DRAFTER_MODEL", "gemini-3.8-flash")
DRAFTED_BY = "Ask about Amma"


def _draft(db: Database, question: str) -> str:
    prompt = (
        "You answer questions from a family about their mother's lab results, using her record below. The data is "
        "synthetic. Families want a clear answer: start with yes or no where the question allows it, then give the "
        "reason from her record in one short sentence.\n\n"
        f"Her verified lab values: {json.dumps(visitprep._history(db))}\n\nQuestion: {question}"
    )
    client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
    return client.models.generate_content(model=DRAFTER_MODEL, contents=prompt).text.strip()


def answer(db: Database, ask_id) -> dict:
    ask = db.asks.find_one({"_id": ask_id})
    if not ask or ask.get("status") != "pending":
        return ask or {}
    db.asks.update_one({"_id": ask_id}, {"$set": {"status": "checking"}})
    draft = _draft(db, ask["question"])
    checked = policy.check(db, [draft], DRAFTED_BY, actor=ask["member_id"], answering=ask["question"])[0]
    update = {"status": "answered", "reply": checked["text"], "blocked": checked["blocked"],
              "drafter": DRAFTER_MODEL, "answered_at": datetime.now(timezone.utc)}
    db.asks.update_one({"_id": ask_id}, {"$set": update})
    return {**ask, **update}
