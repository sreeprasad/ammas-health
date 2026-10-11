"""Advance a run from its last checkpoint: read, verify, record, confirm."""

from datetime import datetime, timezone

from bson import ObjectId
from pymongo.database import Database

from pipeline import checkpoints, memory, notes, reader, recorder, rules, verifier, writer


def _report_date(reading: dict, report: dict) -> datetime:
    if reading.get("collected_date"):
        try:
            return datetime.fromisoformat(reading["collected_date"]).replace(tzinfo=timezone.utc)
        except ValueError:
            pass
    return report["uploaded_at"]


def advance(db: Database, run_id: ObjectId) -> str:
    """Run every step not yet checkpointed. Returns the run status after this call."""
    run = checkpoints.load_run(db, run_id)
    if run["status"] == "complete":
        return "complete"
    report = db.reports.find_one({"_id": run["report_id"]})
    done = checkpoints.completed_steps(run)
    step = None
    try:
        if "read" not in done:
            step = "read"
            started = checkpoints.begin_step(db, run_id, step)
            reading = reader.read_report(db, report["_id"])
            checkpoints.save_step(db, run_id, step, reading, started,
                                  f"{len(reading['values'])} values read · {reading['gemini_calls']} Gemini calls")
            run = checkpoints.load_run(db, run_id)
        reading = run["outputs"]["read"]
        report_date = _report_date(reading, report)

        if "verify" not in done:
            step = "verify"
            started = checkpoints.begin_step(db, run_id, step)
            verification = verifier.verify(db, reading, report_date, rules.live_rule(db))
            checkpoints.save_step(db, run_id, step, verification, started,
                                  f"{verification['verified']} verified · {verification['needs_person']} need a person")
            run = checkpoints.load_run(db, run_id)
        verification = run["outputs"]["verify"]

        if "record" not in done:
            step = "record"
            started = checkpoints.begin_step(db, run_id, step)
            recorded = recorder.record_values(db, report, run_id, report_date, verification)
            checkpoints.save_step(db, run_id, step, recorded, started, f"{recorded['written']} values recorded")
            db.reports.update_one({"_id": report["_id"]}, {"$set": {"report_date": report_date, "run_id": run_id}})

        mem = memory.for_amma(session_id=f"run-{run_id}")
        if "remember" not in done:
            step = "remember"
            started = checkpoints.begin_step(db, run_id, step)
            counts = writer.remember_report_values(db, mem, report["_id"], run_id)
            checkpoints.save_step(db, run_id, step, counts, started,
                                  f"{counts['semantic']} facts · {counts['taxonomic']} new terms · {counts['held']} held")

        step = "confirm"
        if recorder.apply_answers(db, run_id):
            writer.remember_report_values(db, mem, report["_id"], run_id)
        waiting = [v["_id"] for v in db["values"].find({"report_id": report["_id"], "status": "needs_person"}, {"_id": 1})]
        if waiting:
            checkpoints.pause(db, run_id, waiting)
            db.reports.update_one({"_id": report["_id"]}, {"$set": {"status": "paused"}})
            return "paused"
        if "confirm" not in done:
            started = checkpoints.begin_step(db, run_id, step)
            checkpoints.save_step(db, run_id, step, {}, started, "every value verified")

        if "visit" not in done:
            step = "visit"
            started = checkpoints.begin_step(db, run_id, step)
            visit_date = report_date.date().isoformat()
            note = notes.note_on(db, visit_date)
            writer.remember_visit(db, mem, visit_date, f"Lab visit {visit_date}",
                                  writer.visit_content(db, [report["_id"]], note), ["lab-visit"], run_id)
            checkpoints.save_step(db, run_id, step, {"visit_date": visit_date}, started, f"episode saved for {visit_date}")
        checkpoints.complete(db, run_id)
        db.reports.update_one({"_id": report["_id"]}, {"$set": {"status": "complete"}})
        return "complete"
    except Exception as e:
        checkpoints.fail(db, run_id, step or "unknown", f"{type(e).__name__}: {e}")
        raise
