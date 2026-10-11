"""Hand runs to the amma-harness agent on Agent Engine: invoke for a new report, resume for an answer."""

import os
from datetime import datetime, timezone

import requests
from bson import ObjectId
from pymongo.database import Database

USER_ID = "amma"


def invoke_url() -> str | None:
    return os.environ.get("AGENT_INVOKE_URL")


def _post(body: dict) -> dict:
    response = requests.post(invoke_url(), json={**body, "user_id": USER_ID}, timeout=600)
    response.raise_for_status()
    return response.json()


def _record(db: Database, report_id: ObjectId, result: dict) -> str:
    interrupts = (result.get("suspend_context") or {}).get("interrupts") or []
    db.runs.update_one({"report_id": report_id}, {"$set": {"agent": {
        "session_id": result.get("session_id"),
        "execution_id": result.get("execution_id"),
        "status": result.get("status"),
        "interrupt_id": interrupts[0]["id"] if interrupts else None,
        "error": result.get("error"),
        "updated_at": datetime.now(timezone.utc),
    }}})
    return result.get("status", "unknown")


def start(db: Database, report_id: ObjectId) -> str:
    return _record(db, report_id, _post({"message": f"process report {report_id}"}))


def resume(db: Database, run_id: ObjectId, value: float) -> str:
    run = db.runs.find_one({"_id": run_id})
    agent = run.get("agent") or {}
    if agent.get("status") != "suspended" or not agent.get("interrupt_id"):
        return "not-suspended"
    result = _post({"session_id": agent["session_id"], "resume_map": {agent["interrupt_id"]: {"value": value}}})
    return _record(db, run["report_id"], result)
