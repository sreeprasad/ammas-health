"""Watch Atlas for new reports and answers, and advance their runs.

On start it sweeps for work missed while it was down, then follows change streams.
With AGENT_INVOKE_URL set, runs go to the amma-harness agent on Agent Engine; otherwise they run here.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import checkpoints, recorder, run, watcher  # noqa: E402
from pipeline.db import get_db  # noqa: E402
from worker import agent_client  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s | worker | %(message)s")
log = logging.getLogger(__name__)


def handle(db, run_id) -> None:
    status = run.advance(db, run_id)
    log.info("run %s -> %s", run_id, status)


def start_report(db, report_id) -> None:
    db.reports.update_one({"_id": report_id, "status": "uploaded"}, {"$set": {"status": "processing"}})
    if agent_client.invoke_url():
        log.info("report %s -> agent: %s", report_id, agent_client.start(db, report_id))
        return
    handle(db, checkpoints.start_run(db, report_id)["_id"])


def handle_answer(db, answer) -> None:
    if agent_client.invoke_url():
        # The family's answer is the source of truth, so the value flips now; the resumed agent run
        # then does the governed part (memory writes, completing the run).
        recorder.apply_answers(db, answer["run_id"])
        status = agent_client.resume(db, answer["run_id"], answer["value"])
        log.info("answer for run %s -> agent: %s", answer["run_id"], status)
        return
    handle(db, answer["run_id"])


def sweep(db) -> None:
    for report in db.reports.find({"status": {"$in": ["uploaded", "processing"]}}):
        log.info("sweep: report %s", report["_id"])
        start_report(db, report["_id"])
    if not agent_client.invoke_url():
        for r in db.runs.find({"status": "running"}):
            log.info("sweep: unfinished run %s", r["_id"])
            handle(db, r["_id"])
    for answer in db.answers.find({"applied": {"$ne": True}}):
        log.info("sweep: answer waiting for run %s", answer["run_id"])
        handle_answer(db, answer)


def run_watcher(db, trigger: str) -> None:
    out = watcher.run(db, trigger=trigger)
    log.info("watcher (%s): %d checked, %d need attention, next run %s", trigger, out["checked"], out["need_attention"],
             out["next_run"].isoformat())


def main() -> None:
    db = get_db()
    sweep(db)
    watch = [{"$match": {"operationType": "insert", "ns.coll": {"$in": ["reports", "answers", "watcher_jobs"]}}}]
    log.info("watching reports, answers and watcher jobs (%s)", "agent: " + agent_client.invoke_url() if agent_client.invoke_url() else "local")
    with db.watch(watch, max_await_time_ms=30000) as stream:
        while stream.alive:
            change = stream.try_next()
            if change is None:
                if watcher.due(db):
                    run_watcher(db, "schedule")
                continue
            doc = change["fullDocument"]
            try:
                if change["ns"]["coll"] == "reports" and doc.get("status") == "uploaded":
                    log.info("new report %s", doc["_id"])
                    start_report(db, doc["_id"])
                elif change["ns"]["coll"] == "watcher_jobs":
                    run_watcher(db, f"run now by {doc.get('requested_by', 'unknown')}")
                elif change["ns"]["coll"] == "answers" and doc.get("via") != "agent-engine-resume":
                    log.info("answer for run %s", doc["run_id"])
                    handle_answer(db, doc)
            except Exception:
                log.exception("step failed; the run keeps its checkpoint")


if __name__ == "__main__":
    main()
