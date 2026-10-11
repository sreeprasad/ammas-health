"""Visit prep: draft what to watch and what to ask at her next visit, then pass every line through the policy."""

import json
import re
from datetime import datetime, timezone
from typing import Literal

from agent_engine_sdk_memory import Memory
from pydantic import BaseModel, Field
from pymongo.database import Database

from pipeline import notes as notes_store, policy
from pipeline.learner import _parse

DRAFTED_BY = "Visit prep"
HEADLINE_TESTS = ["hba1c", "hgb", "ldl", "vitd", "creat", "tsh", "fasting_glucose"]


class WatchLine(BaseModel):
    tag: Literal["RISING", "LOW", "NEW", "GOOD"]
    text: str


class Draft(BaseModel):
    worth_watching: list[WatchLine] = Field(description="3-5 short factual lines about what changed.")
    questions: list[str] = Field(description="3-5 questions the family can ask her doctor.")
    family_notes: list[str] = Field(description="2-3 practical notes for the family before the visit.")
    next_steps: list[str] = Field(description="2-3 next steps for her care that the family is likely to ask about.")


def _history(db: Database) -> dict:
    out = {}
    for test in HEADLINE_TESTS:
        rows = list(db["values"].find({"test": test, "status": "verified"},
                                      {"_id": 0, "report_date": 1, "value_text": 1, "unit": 1, "range": 1}).sort("report_date", 1))
        if rows:
            out[test] = {"unit": rows[-1]["unit"], "range": rows[-1]["range"]["text"],
                         "values": [f"{r['report_date'].date().isoformat()}: {r['value_text']}" for r in rows]}
    return out


def next_visit(db: Database) -> dict | None:
    for note in notes_store.all_notes(db):
        m = re.search(r"review booked for ([A-Z][a-z]{2} \d{1,2})", note["text"])
        if m:
            return {"department": note["department"], "label": m.group(1)}
    return None


def draft(db: Database, mem: Memory, run_id=None) -> dict:
    visit = next_visit(db)
    context = mem.build_context(query="What changed in her lab results this year and what did her doctors ask for?",
                                enabled_sources={"semantic", "episodic", "taxonomic", "procedural"})
    notes = [{"date": n["date"], "department": n["department"], "text": n["text"]} for n in notes_store.all_notes(db)]
    prompt = f"""Prepare a one-page summary for a family taking their mother to her next visit
({visit['department'] + ' on ' + visit['label'] if visit else 'next visit'}). The data is synthetic.

Her verified lab values by test:
{json.dumps(_history(db), indent=2)}

Doctor notes:
{json.dumps(notes, indent=2)}

What her record remembers:
{context.formatted_context or ''}

Write plain, short lines a family member can read in a minute."""
    d = _parse(prompt, Draft)

    watch = policy.check(db, [w.text for w in d.worth_watching], DRAFTED_BY, run_id)
    questions = policy.check(db, d.questions, DRAFTED_BY, run_id)
    family_notes = policy.check(db, d.family_notes + d.next_steps, DRAFTED_BY, run_id)
    doc = {
        "at": datetime.now(timezone.utc),
        "visit": visit,
        "worth_watching": [{"tag": w.tag, **r} for w, r in zip(d.worth_watching, watch)],
        "questions": questions,
        "family_notes": family_notes,
        "blocked": sum(1 for r in watch + questions + family_notes if r["blocked"]),
        "run_id": run_id,
    }
    db.visit_prep.insert_one(doc)
    return doc
