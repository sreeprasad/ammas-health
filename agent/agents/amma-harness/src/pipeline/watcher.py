"""Watcher: follow-ups pulled from the doctor's notes, tracked against later reports until they happen.

Claude only extracts what each note asked for; matching against her reports and the verdicts are plain code.
"""

import json
from datetime import date, datetime, timedelta, timezone
from typing import Literal

from pydantic import BaseModel, Field
from pymongo.database import Database

from pipeline import notes as notes_store
from pipeline.learner import _parse

CADENCE = timedelta(days=7)
ON_TIME_GRACE = timedelta(days=14)
UNRESOLVED_AFTER = timedelta(days=30)


class FollowUp(BaseModel):
    note_id: str
    quote: str = Field(description="The exact words from the note that ask for the follow-up.")
    kind: Literal["retest", "watch", "lifestyle", "appointment"]
    test_id: str | None = Field(description="One of the known test ids. For a retest, the test to repeat (null if any "
                                            "new labs will do). For a watch item about a symptom, the test most related "
                                            "to it. Else null.")
    due_in_days: int | None = Field(description="Days after the note when it is due, if the note gives a time.")
    due_date: str | None = Field(description="YYYY-MM-DD if the note names a date; if it names only a month, the last "
                                             "day of that month in the note's year. Else null.")


class FollowUps(BaseModel):
    followups: list[FollowUp]


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _day(d) -> date:
    return d.date() if isinstance(d, datetime) else date.fromisoformat(d)


def _label(d: date) -> str:
    return d.strftime("%b %-d")


def extract(db: Database) -> int:
    notes = [{k: n[k] for k in ("note_id", "date", "department", "text")} for n in notes_store.all_notes(db)]
    tests = {row["_id"]: row["name"] for row in db["values"].aggregate([
        {"$match": {"standard_name": {"$exists": True}}}, {"$group": {"_id": "$test", "name": {"$first": "$standard_name"}}}])}
    prompt = ("Extract the follow-ups a doctor asked for in these notes: a test to repeat, something to watch, a "
              "lifestyle action someone must arrange, or a booked appointment. Skip ongoing advice to continue as "
              "before. One item per request; quote the note's own words. Use only these test ids:\n"
              + json.dumps(tests) + "\n\nNotes:\n" + json.dumps(notes, indent=2))
    found = _parse(prompt, FollowUps).followups
    dates = {n["note_id"]: n["date"] for n in notes}
    for f in found:
        said_on = dates.get(f.note_id)
        if not said_on:
            continue
        due = f.due_date or ((_day(said_on) + timedelta(days=f.due_in_days)).isoformat() if f.due_in_days else None)
        db.followups.update_one(
            {"note_id": f.note_id, "quote": f.quote},
            {"$set": {"kind": f.kind, "test": f.test_id, "said_on": said_on, "due": due},
             "$setOnInsert": {"created_at": _now(), "status": "open"}},
            upsert=True)
    return len(found)


def _verified_after(db: Database, test: str, after: date) -> list[dict]:
    return list(db["values"].find({"test": test, "status": "verified",
                                   "report_date": {"$gt": datetime(after.year, after.month, after.day, tzinfo=timezone.utc)}})
                .sort("report_date", 1))


def evaluate(db: Database, f: dict, today: date) -> dict:
    said_on = _day(f["said_on"])
    due = _day(f["due"]) if f.get("due") else None

    if f["kind"] == "appointment" and due:
        if today <= due:
            wake = due + timedelta(days=1)
            return {"status": "scheduled", "wake_on": wake.isoformat(),
                    "summary": f"Will wake {_label(wake)} to read the new doctor's note"}
        return {"status": "awaiting note", "summary": f"Visit on {_label(due)} passed; waiting for the doctor's note"}

    if f["kind"] == "retest" and not f.get("test"):
        start = max(said_on, due - timedelta(days=30)) if due else said_on
        report = db.reports.find_one({"report_date": {"$gt": datetime(start.year, start.month, start.day, tzinfo=timezone.utc)}},
                                     sort=[("report_date", 1)])
        if report:
            when = _day(report["report_date"])
            on_time = due is None or when <= due + ON_TIME_GRACE
            return {"status": "done", "met_on": when.isoformat(), "summary": f"New labs on {_label(when)}, {'on time' if on_time else 'late'}"}
        return {"status": "open", "summary": "Waiting for new labs"}

    if f["kind"] == "retest" and f.get("test"):
        later = _verified_after(db, f["test"], said_on)
        if later:
            when = _day(later[0]["report_date"])
            on_time = due is None or when <= due + ON_TIME_GRACE
            return {"status": "done", "met_on": when.isoformat(),
                    "summary": f"Retested {_label(when)}, {'on time' if on_time else 'late'}"}
        if due and today > due:
            return {"status": "overdue", "summary": f"Not retested; due {_label(due)}"}
        next_labs = db.reports.find_one({"report_date": {"$gt": datetime(said_on.year, said_on.month, said_on.day, tzinfo=timezone.utc)}},
                                        sort=[("report_date", 1)])
        if due is None and next_labs:
            return {"status": "overdue", "summary": f"Not repeated on the {_label(_day(next_labs['report_date']))} labs"}
        return {"status": "open", "summary": f"Waiting for a retest by {_label(due) if due else 'the next labs'}"}

    if f["kind"] == "watch" and f.get("test"):
        later = _verified_after(db, f["test"], said_on)
        before = db["values"].find_one({"test": f["test"], "status": "verified",
                                        "report_date": {"$lte": datetime(said_on.year, said_on.month, said_on.day, tzinfo=timezone.utc)}},
                                       sort=[("report_date", -1)])
        if later and before and later[-1]["value"] < before["value"]:
            named = db["values"].find_one({"test": f["test"], "standard_name": {"$exists": True}}, {"standard_name": 1})
            name = named["standard_name"] if named else f["test"]
            return {"status": "flagged", "linked_value_id": later[-1]["_id"],
                    "summary": f"{name} fell again on {_label(_day(later[-1]['report_date']))} → linked and flagged"}
        return {"status": "watching", "summary": "Watching; no change on later reports yet"}

    age = today - said_on
    if age > UNRESOLVED_AFTER:
        return {"status": "unresolved", "add_to_questions": True,
                "summary": f"No record after {age.days} days → added to the next visit's questions"}
    return {"status": "open", "summary": "Waiting for a record"}


def run(db: Database, trigger: str = "schedule", today: date | None = None) -> dict:
    today = today or _now().date()
    if not db.followups.count_documents({}):
        extract(db)
    results = []
    for f in db.followups.find().sort("said_on", 1):
        verdict = evaluate(db, f, today)
        db.followups.update_one({"_id": f["_id"]}, {"$set": {**verdict, "checked_at": _now()}})
        results.append({"said_on": f["said_on"], "quote": f["quote"], **verdict})
    now = _now()
    state = {"last_run": now, "next_run": now + CADENCE, "trigger": trigger,
             "checked": len(results), "need_attention": sum(r["status"] in ("overdue", "unresolved", "flagged") for r in results)}
    db.watcher_state.update_one({"_id": "watcher"}, {"$set": state}, upsert=True)
    db.audit_log.insert_one({"at": now, "event": "WATCHED", "actor": "Watcher", "policy": "follow-ups",
                             "what": f"{state['checked']} follow-ups checked · {state['need_attention']} need attention ({trigger})"})
    return {**state, "results": results}


def due(db: Database) -> bool:
    state = db.watcher_state.find_one({"_id": "watcher"})
    return state is None or state["next_run"] <= _now()
