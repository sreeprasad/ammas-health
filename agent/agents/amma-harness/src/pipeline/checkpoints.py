"""Run checkpoints in the runs collection: one saved output per completed step."""

from datetime import datetime, timezone

from bson import ObjectId
from pymongo import ReturnDocument
from pymongo.database import Database


def _now() -> datetime:
    return datetime.now(timezone.utc)


def start_run(db: Database, report_id: ObjectId) -> dict:
    """Create the run for a report, or return the existing one."""
    now = _now()
    return db.runs.find_one_and_update(
        {"report_id": report_id},
        {"$setOnInsert": {"report_id": report_id, "status": "running", "steps": [], "outputs": {},
                          "executions": {}, "created_at": now, "updated_at": now}},
        upsert=True,
        return_document=ReturnDocument.AFTER,
    )


def load_run(db: Database, run_id: ObjectId) -> dict:
    return db.runs.find_one({"_id": run_id})


def completed_steps(run: dict) -> set[str]:
    return {s["name"] for s in run["steps"] if s["status"] == "done"}


def begin_step(db: Database, run_id: ObjectId, step: str) -> datetime:
    started = _now()
    db.runs.update_one({"_id": run_id}, {"$inc": {f"executions.{step}": 1},
                                         "$set": {"status": "running", "current_step": step, "updated_at": started}})
    return started


def save_step(db: Database, run_id: ObjectId, step: str, output: dict, started: datetime, summary: str) -> None:
    ended = _now()
    db.runs.update_one({"_id": run_id}, {
        "$push": {"steps": {"name": step, "status": "done", "summary": summary, "started_at": started,
                            "ended_at": ended, "duration_ms": int((ended - started).total_seconds() * 1000)}},
        "$set": {f"outputs.{step}": output, "updated_at": ended},
    })


def pause(db: Database, run_id: ObjectId, waiting_on: list[ObjectId]) -> None:
    db.runs.update_one({"_id": run_id}, {"$set": {"status": "paused", "waiting_on": waiting_on, "updated_at": _now()}})


def complete(db: Database, run_id: ObjectId) -> None:
    now = _now()
    db.runs.update_one({"_id": run_id}, {"$set": {"status": "complete", "current_step": None, "waiting_on": [],
                                                  "completed_at": now, "updated_at": now}})


def fail(db: Database, run_id: ObjectId, step: str, error: str) -> None:
    db.runs.update_one({"_id": run_id}, {"$set": {"status": "failed", "failed_step": step, "error": error,
                                                  "updated_at": _now()}})
