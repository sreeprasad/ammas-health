"""Watch Atlas for new reports and answers, and advance their runs.

On start it sweeps for work missed while it was down, then follows change streams.
"""

import logging
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import checkpoints, run  # noqa: E402
from pipeline.db import get_db  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s | worker | %(message)s")
log = logging.getLogger(__name__)


def handle(db, run_id) -> None:
    status = run.advance(db, run_id)
    log.info("run %s -> %s", run_id, status)


def start_report(db, report_id) -> None:
    db.reports.update_one({"_id": report_id, "status": "uploaded"}, {"$set": {"status": "processing"}})
    handle(db, checkpoints.start_run(db, report_id)["_id"])


def sweep(db) -> None:
    for report in db.reports.find({"status": {"$in": ["uploaded", "processing"]}}):
        log.info("sweep: report %s", report["_id"])
        start_report(db, report["_id"])
    for r in db.runs.find({"status": "running"}):
        log.info("sweep: unfinished run %s", r["_id"])
        handle(db, r["_id"])
    for run_id in db.answers.distinct("run_id", {"applied": {"$ne": True}}):
        log.info("sweep: answers waiting for run %s", run_id)
        handle(db, run_id)


def main() -> None:
    db = get_db()
    sweep(db)
    watch = [{"$match": {"operationType": "insert", "ns.coll": {"$in": ["reports", "answers"]}}}]
    log.info("watching reports and answers")
    with db.watch(watch) as stream:
        for change in stream:
            doc = change["fullDocument"]
            try:
                if change["ns"]["coll"] == "reports" and doc.get("status") == "uploaded":
                    log.info("new report %s", doc["_id"])
                    start_report(db, doc["_id"])
                elif change["ns"]["coll"] == "answers":
                    log.info("answer for run %s", doc["run_id"])
                    handle(db, doc["run_id"])
            except Exception:
                log.exception("step failed; the run keeps its checkpoint")


if __name__ == "__main__":
    main()
