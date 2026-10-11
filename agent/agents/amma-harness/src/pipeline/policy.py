"""Policy summarize-never-treat: no line shown to the family may advise treatment.

A separate Claude call classifies each draft line; advice is blocked, rewritten as a question for her doctor,
and logged as BLOCKED with the identity of the step that drafted it.
"""

import json
from datetime import datetime, timezone

from pydantic import BaseModel, Field
from pymongo.database import Database

from pipeline.learner import _parse

POLICY = "summarize-never-treat"


class Verdict(BaseModel):
    index: int
    treatment_advice: bool = Field(description="True if the line tells anyone to start, stop, change or dose a "
                                               "medicine, supplement, diet or therapy, or recommends a treatment.")
    question_for_doctor: str = Field(description="If treatment_advice, the same concern rewritten as a neutral "
                                                 "question the family can ask her doctor. Otherwise empty.")


class Verdicts(BaseModel):
    verdicts: list[Verdict]


def check(db: Database, lines: list[str], drafted_by: str, run_id=None) -> list[dict]:
    """Return one result per line: the text to show, and whether the original was blocked."""
    if not lines:
        return []
    prompt = (
        "You enforce a policy for a family health record: it may summarize lab values and raise questions for the "
        "doctor, but it must never give treatment advice. Judge each numbered line on its own.\n"
        + json.dumps([{"index": i, "line": line} for i, line in enumerate(lines)], indent=2)
    )
    verdicts = {v.index: v for v in _parse(prompt, Verdicts).verdicts}
    results = []
    for i, line in enumerate(lines):
        v = verdicts.get(i)
        if v and v.treatment_advice and v.question_for_doctor.strip():
            db.audit_log.insert_one({
                "at": datetime.now(timezone.utc), "event": "BLOCKED", "actor": drafted_by, "policy": POLICY,
                "what": f'{drafted_by} drafted "{line}" Rewritten as a question for the doctor.',
                "rewritten": v.question_for_doctor.strip(), "run_id": run_id,
            })
            results.append({"text": v.question_for_doctor.strip(), "blocked": line})
        else:
            results.append({"text": line, "blocked": None})
    return results
