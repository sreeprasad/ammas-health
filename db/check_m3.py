"""M3 check: "HGB" finds Hemoglobin history, and the paused LDL is provably absent from memory until confirmed."""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import checkpoints, memory, replay, run, search  # noqa: E402
from pipeline.db import get_db  # noqa: E402

TRUTH = ROOT / "data" / "truth" / "2026-09-12_full-panel.json"
results: list[bool] = []


def check(ok: bool, message: str) -> None:
    results.append(ok)
    print(f"{'PASS' if ok else 'FAIL'} {message}")


def ldl_fact(mem) -> str:
    fact = mem.get_semantic("lab-ldl") or {}
    return fact.get("content", "") if isinstance(fact, dict) else getattr(fact, "content", "")


def main() -> int:
    db = get_db()
    mem = memory.for_amma(session_id="check-m3")
    print("reset:", replay.reset_uploads(db, mem))

    hits = search.search_history(db, mem, "HGB")
    top = hits[0] if hits else {}
    check(top.get("test") == "hgb" and top.get("name") == "Hemoglobin",
          f'search "HGB" -> {top.get("name")} (memory leg found it: {top.get("from_memory")})')
    check(top.get("test") == "hgb" and len(top.get("history", [])) >= 4,
          f"{top.get('name')} history: {[h['value_text'] for h in top.get('history', [])]}")

    truth = json.loads(TRUTH.read_text())
    photos = [ROOT / "data" / p["file"] for p in truth["files"]["photos"]]
    report_id = replay.ingest_photos(db, photos, "sreeprasad", truth["report_key"])
    run_id = checkpoints.start_run(db, report_id)["_id"]
    status = run.advance(db, run_id)
    check(status == "paused", f"Sep 12 run paused (status {status})")

    ldl = db["values"].find_one({"report_id": report_id, "printed_name": "LDL-C"})
    check(ldl["status"] == "needs_person" and not ldl.get("memory_written_at"),
          f'LDL "{ldl["value_text"]}" is {ldl["status"]}, never written to memory')
    check(db.audit_log.find_one({"event": "HELD", "value_id": ldl["_id"]}) is not None, "HELD event in audit_log")
    fact = ldl_fact(mem)
    check("104" not in fact and "1?4" not in fact, f"memory fact lab-ldl while paused: {fact!r}")
    leaked = [c for c in mem.search("LDL 1?4", sources=["semantic", "episodic", "taxonomic"], top_k=20)
              if "1?4" in (getattr(c, "content", "") or "")]
    check(not leaked, f"no memory chunk contains the unconfirmed reading ({len(leaked)} found)")
    written_hgb = db["values"].find_one({"report_id": report_id, "test": "hgb"})
    check(bool(written_hgb.get("memory_written_at")), "verified Sep 12 values were written while LDL was held")

    db.answers.insert_one({"run_id": run_id, "value_id": ldl["_id"], "value": 104, "member_id": "sreeprasad",
                           "at": datetime.now(timezone.utc), "applied": False})
    status = run.advance(db, run_id)
    check(status == "complete", f"run complete after the answer (status {status})")
    fact = ldl_fact(mem)
    check("104" in fact, f"memory fact lab-ldl after confirmation: {fact!r}")
    check(db.audit_log.find_one({"event": "RELEASED", "value_id": ldl["_id"]}) is not None, "RELEASED event in audit_log")

    context = mem.build_context(query="How is her cholesterol and what does LDL-C mean?",
                                enabled_sources={"semantic", "episodic", "taxonomic", "procedural"})
    text = context.formatted_context or ""
    check("104" in text, f"build_context over all four sources mentions the confirmed LDL ({len(text)} chars)")

    by_kind = {row["_id"]: row["n"] for row in db.memory_writes.aggregate([{"$group": {"_id": "$kind", "n": {"$sum": 1}}}])}
    check(all(by_kind.get(k) for k in ["semantic", "episodic", "taxonomic", "procedural"]), f"memory writes by type: {by_kind}")
    return 0 if all(results) else 1


if __name__ == "__main__":
    sys.exit(main())
