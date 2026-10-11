"""M6 check: the audit log shows HELD, BLOCKED, DENIED and REJECTED, each with an identity; plus Watcher and encryption.

Needs the web app running (npm run dev in web/, default http://localhost:3100).
"""

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

import requests

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from evalrunner.learn import learn  # noqa: E402
from pipeline import checkpoints, memory, notes, policy, replay, run, visitprep, watcher  # noqa: E402
from pipeline.db import get_db  # noqa: E402

WEB = os.environ.get("WEB_URL", "http://localhost:3100")
TRUTH = ROOT / "data" / "truth" / "2026-09-12_full-panel.json"
SELF_TEST = ["Reduce her vitamin D dose now that it is in range.", "Vitamin D rose from 14 to 32 ng/mL."]
results: list[bool] = []


def check(ok: bool, message: str) -> None:
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'} {message}")


def main() -> int:
    db = get_db()
    mem = memory.for_amma(session_id="check-m6")
    start = datetime.now(timezone.utc)
    print("reset:", replay.reset_rules(db), replay.reset_uploads(db, mem))

    truth = json.loads(TRUTH.read_text())
    report_id = replay.ingest_photos(db, [ROOT / "data" / p["file"] for p in truth["files"]["photos"]], "sreeprasad", truth["report_key"])
    run_id = checkpoints.start_run(db, report_id)["_id"]
    status = run.advance(db, run_id)
    ldl = db["values"].find_one({"run_id": run_id, "status": "needs_person"})
    db.answers.insert_one({"run_id": run_id, "value_id": ldl["_id"], "value": 104, "member_id": "sreeprasad",
                           "at": datetime.now(timezone.utc), "applied": False})
    status = f"{status} -> {run.advance(db, run_id)}"
    print(f"Sep 12 run: {status}")

    prep = visitprep.draft(db, mem, run_id)
    print(f"visit prep: {len(prep['questions'])} questions, {prep['blocked']} line(s) blocked from real drafts")
    tested = policy.check(db, SELF_TEST, "policy self-test", run_id)
    db.audit_log.update_many({"actor": "policy self-test", "at": {"$gte": start}}, {"$set": {"test": True}})
    check(tested[0]["blocked"] is not None and tested[1]["blocked"] is None,
          f'policy self-test: advice blocked -> "{tested[0]["text"]}"; plain fact allowed')

    denied = requests.get(f"{WEB}/api/family", headers={"x-member-id": "aide"}, timeout=30)
    allowed_meds = requests.get(f"{WEB}/api/medications", headers={"x-member-id": "aide"}, timeout=30)
    check(denied.status_code == 403 and allowed_meds.status_code == 200,
          f"aide: lab values -> {denied.status_code}, medications -> {allowed_meds.status_code}")

    outcome = learn()
    check(outcome.get("promoted") == "v4", f"learning check promoted {outcome.get('promoted')}")

    print("\naudit_log since the check started:")
    events = list(db.audit_log.find({"at": {"$gte": start}}).sort("at", 1))
    for e in events:
        if e["event"] in ("HELD", "BLOCKED", "DENIED", "REJECTED", "PROMOTED", "RELEASED", "ALLOWED"):
            tag = " [self-test]" if e.get("test") else ""
            print(f"  {e['event']:9} actor={e.get('actor')!s:18} policy={e.get('policy')!s:26} {e['what'][:80]}{tag}")
    for name in ["HELD", "BLOCKED", "DENIED", "REJECTED"]:
        found = [e for e in events if e["event"] == name]
        check(bool(found) and all(e.get("actor") and e.get("policy") for e in found),
              f"{name}: {len(found)} event(s), every one with an actor and a policy")

    db.followups.delete_many({})
    out = watcher.run(db, trigger="check")
    by_status = {}
    for r in out["results"]:
        by_status[r["status"]] = by_status.get(r["status"], 0) + 1
    check(out["checked"] >= 5 and by_status.get("done", 0) >= 2 and by_status.get("scheduled") == 1,
          f"watcher: {out['checked']} follow-ups {by_status}, next run {out['next_run']:%b %d}")

    raw = db.notes.find_one({"note_id": "note-2026-07-22"})
    decrypted = next(n for n in notes.all_notes(db) if n["note_id"] == "note-2026-07-22")
    check("text" not in raw and raw["text_enc"].subtype == 6 and "tiredness" in decrypted["text"],
          "doctor-note text stored only as ciphertext (subtype 6) and decrypts with the key")
    check(b"tiredness" not in raw["text_enc"], "ciphertext does not contain the plaintext")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
