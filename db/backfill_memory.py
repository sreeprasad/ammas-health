"""Write the seeded history into Agent Engine memory: facts, terms, one episode per visit, reading rules."""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import memory, writer  # noqa: E402
from pipeline.db import get_db  # noqa: E402
from pipeline.verifier import RULE_V3  # noqa: E402


def main() -> None:
    db = get_db()
    mem = memory.for_amma(session_id="backfill")
    totals = {"semantic": 0, "taxonomic": 0, "held": 0, "older": 0}

    for report in db.reports.find({"report_date": {"$exists": True}}).sort("report_date", 1):
        counts = writer.remember_report_values(db, mem, report["_id"], run_id=None, actor="backfill")
        for k in totals:
            totals[k] += counts[k]

    visits = sorted(db.reports.distinct("report_date", {"source": "seed"}))
    for when in visits:
        day = when.date().isoformat()
        report_ids = db.reports.distinct("_id", {"source": "seed", "report_date": when})
        note = db.notes.find_one({"date": day})
        title = f"{note['department']} visit {day}" if note else f"Lab visit {day}"
        writer.remember_visit(db, mem, day, title, writer.visit_content(db, report_ids, note),
                              ["visit", "doctor-note"] if note else ["visit"], run_id=None)

    writer.remember_procedure(db, mem, RULE_V3, run_id=None)
    print(f"semantic facts: {totals['semantic']} (older values skipped: {totals['older']}) · "
          f"taxonomic terms: {totals['taxonomic']} · episodes: {len(visits)} · procedures: 1 · held: {totals['held']}")


if __name__ == "__main__":
    main()
