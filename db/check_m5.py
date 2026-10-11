"""M5 check: from the family's LDL answer, v4 and v4-alt are drafted, scored on the 22 older reports against
eval_vault, v4-alt is rejected for regressions and v4 is promoted with none. Everything is computed live."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evalrunner.learn import learn  # noqa: E402
from pipeline import checkpoints, memory, replay, rules, run  # noqa: E402
from pipeline.db import get_db  # noqa: E402

TRUTH = ROOT / "data" / "truth" / "2026-09-12_full-panel.json"
results: list[bool] = []


def check(ok: bool, message: str) -> None:
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'} {message}")


def run_sep12(db, answer: float | None) -> tuple:
    truth = json.loads(TRUTH.read_text())
    report_id = replay.ingest_photos(db, [ROOT / "data" / p["file"] for p in truth["files"]["photos"]],
                                     "sreeprasad", truth["report_key"])
    run_id = checkpoints.start_run(db, report_id)["_id"]
    status = run.advance(db, run_id)
    if answer is not None and status == "paused":
        ldl = db["values"].find_one({"run_id": run_id, "status": "needs_person"})
        db.answers.insert_one({"run_id": run_id, "value_id": ldl["_id"], "value": answer, "member_id": "sreeprasad",
                               "at": datetime.now(timezone.utc), "applied": False})
        status = run.advance(db, run_id)
    return run_id, status


def main() -> int:
    db = get_db()
    mem = memory.for_amma(session_id="check-m5")
    print("reset:", replay.reset_rules(db), replay.reset_uploads(db, mem))
    check(rules.live_rule(db)["version"] == "v3", "starting rule is v3")

    run_id, status = run_sep12(db, answer=104)
    check(status == "complete", f"Sep 12 run completed after the family answered 104 ({status})")

    outcome = learn()
    by_version = {c["version"]: c for c in outcome["candidates"]}
    base = outcome["baseline"]
    v4, alt = by_version.get("v4", {}), by_version.get("v4-alt", {})
    check(alt and not alt["passes"] and alt["regressions"] > 0,
          f"v4-alt rejected: {alt.get('correct')}/{alt.get('total')} with {alt.get('regressions')} regression(s)")
    check(v4 and v4["passes"] and v4["regressions"] == 0 and v4["correct"] >= base["correct"],
          f"v4 passes: {v4.get('correct')}/{v4.get('total')} vs v3 {base['correct']}/{base['total']}, 0 regressions")
    check(outcome["promoted"] == "v4", f"promoted: {outcome['promoted']}")
    check(rules.live_rule(db)["version"] == "v4" and db.rules.count_documents({"status": "live"}) == 1, "v4 is the only live rule")
    check(db.memory_writes.find_one({"kind": "procedural", "key": "read-lab-report-v4"}) is not None, "procedural memory holds v4")
    events = {e["event"] for e in db.audit_log.find({"run_id": run_id, "event": {"$in": ["PROMOTED", "REJECTED"]}})}
    check(events == {"PROMOTED", "REJECTED"}, f"audit_log has {sorted(events)} for this run")
    glucose = db["values"].find_one({"run_id": run_id, "printed_name": "Glucose (F)"})
    check(bool(glucose and glucose.get("test")), f"new term learned: Glucose (F) -> {glucose and glucose.get('standard_name')}")

    print("re-running Sep 12 under the promoted rule:")
    print("reset uploads:", replay.reset_uploads(db, mem))
    run_id, status = run_sep12(db, answer=None)
    held = [v["printed_name"] for v in db["values"].find({"run_id": run_id, "status": "needs_person"})]
    check(status == "paused" and "LDL-C" in held, f"under v4 the smudged LDL still pauses (holding {held})")
    print(json.dumps(outcome, indent=2, default=str))
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
