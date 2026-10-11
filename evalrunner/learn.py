"""Learning check: draft rule candidates from the family's latest correction, score them on the 22 older
reports against eval_vault, promote only a candidate with zero regressions, and record everything.

The vault is read only through an eval_runner connection; drafting and promotion use the harness user.
"""

import sys
from datetime import datetime, timezone
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline import learner, memory, rules, writer  # noqa: E402
from pipeline.db import get_db  # noqa: E402
from evalrunner.score import build_cases, regressions, score  # noqa: E402

GATE = "zero-regressions"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _next_version(version: str) -> str:
    return f"v{int(version.lstrip('v').split('-')[0]) + 1}"


def latest_correction(db) -> tuple[dict, dict] | None:
    value = db["values"].find_one({"source": "person"}, sort=[("answered_at", -1)])
    if not value:
        return None
    run = db.runs.find_one({"_id": value["run_id"]})
    seen = next((v for v in run["outputs"]["verify"]["values"]
                 if v["page"] == value["page"] and v["printed_name"] == value["printed_name"]), {})
    correction = {
        "printed_name": value["printed_name"],
        "reader_read_it_as": seen.get("read_as", seen.get("value_text")),
        "reader_confidence": seen.get("confidence"),
        "her_previous_value": seen.get("previous"),
        "what_the_live_rule_did": seen.get("decision", "ask"),
        "family_confirmed_value": value["value"],
        "confirmed_by": value.get("answered_by"),
    }
    return correction, run


def _summary(result: dict) -> dict:
    return {k: result[k] for k in ["correct", "total", "asked", "snapped"]}


def learn_terms(db, mem, run) -> list[dict]:
    unknown = list(db["values"].find({"report_id": run["report_id"], "test": None, "status": "verified"}))
    if not unknown:
        return []
    named = learner.name_terms([{"printed_name": v["printed_name"], "unit": v["unit"], "range": v["range"]["text"]}
                                for v in unknown])
    learned = []
    for term in named:
        db["values"].update_many({"printed_name": term.printed_name, "test": None},
                                 {"$set": {"test": term.test_id, "standard_name": term.standard_name, "learned_term": True}})
        unit = next((v["unit"] for v in unknown if v["printed_name"] == term.printed_name), "")
        writer.remember_term(db, mem, term.printed_name, term.test_id, unit, {term.test_id: term.standard_name}, run["_id"])
        db.audit_log.insert_one({"at": _now(), "event": "TERM_LEARNED", "actor": "learning check",
                                 "what": f'"{term.printed_name}" means {term.standard_name}', "run_id": run["_id"]})
        learned.append(term.model_dump())
    return learned


def learn() -> dict:
    app = get_db("HARNESS_AGENT")
    eval_app = get_db("EVAL_RUNNER")
    vault = eval_app.client["eval_vault"]
    found = latest_correction(app)
    if not found:
        print("no family correction to learn from")
        return {"error": "no correction"}
    correction, run = found
    live = rules.live_rule(app)
    version = _next_version(live["version"])
    print(f"live rule {live['version']}; learning from {correction['printed_name']} read as "
          f"{correction['reader_read_it_as']!r}, confirmed as {correction['family_confirmed_value']:g}")

    drafts = learner.draft_rules(live, correction)
    candidates = [
        {**drafts.learned.model_dump(), "version": version, "proposed_by": "family answer"},
        {**drafts.alternative.model_dump(), "version": f"{version}-alt", "proposed_by": "agent"},
    ]

    cases = build_cases(eval_app, vault)
    reports_tested = len({c["report_key"] for c in cases})
    baseline = score(live, cases)
    print(f"{live['version']} (live): {baseline['correct']}/{baseline['total']} correct, asks {baseline['asked']}")

    results = []
    for c in candidates:
        result = score(c, cases)
        broke = regressions(baseline, result)
        passes = result["correct"] >= baseline["correct"] and not broke
        results.append((c, result, broke, passes))
        print(f"{c['version']} ({c['proposed_by']}): {result['correct']}/{result['total']} correct, asks {result['asked']}, "
              f"snaps {result['snapped']}, regressions {len(broke)} -> {'passes' if passes else 'fails'} the gate")
        for b in broke:
            print(f"    broke: {b['report_key']} {b['printed_name']} truth {b['truth']:g}, recorded {b['final']}")

    passing = [r for r in results if r[3]]
    winner = max(passing, key=lambda r: (r[1]["correct"], -r[1]["asked"]), default=None)
    now = _now()
    for c, result, broke, passes in results:
        promoted = winner is not None and c is winner[0]
        status = "live" if promoted else "rejected" if broke else "not promoted"
        app.rules.replace_one({"version": c["version"]}, {
            **c, "status": status, "created_at": now, "decided_at": now, "trigger_run_id": run["_id"],
            "gate": GATE, "baseline": {"version": live["version"], **_summary(baseline)}, "scores": _summary(result),
            "reports_tested": reports_tested,
            "regressions": [{k: b[k] for k in ["report_key", "printed_name", "truth", "final", "read_text"]} for b in broke],
        }, upsert=True)
        app.audit_log.insert_one({
            "at": now, "event": "PROMOTED" if promoted else "REJECTED", "actor": "learning check", "policy": GATE,
            "what": (f"Rule {c['version']} promoted at {result['correct']} / {result['total']}, 0 regressions" if promoted
                     else f"Rule {c['version']} failed the learning check: {len(broke)} regression(s)" if broke
                     else f"Rule {c['version']} passed but did not beat {winner[0]['version'] if winner else live['version']}"),
            "detail": f"{len(cases)} values across {reports_tested} reports, scored against eval_vault", "run_id": run["_id"],
        })

    mem = memory.for_amma(session_id=f"learning-{run['_id']}")
    if winner:
        app.rules.update_one({"version": live["version"]}, {"$set": {"status": "retired", "retired_at": now}})
        writer.remember_procedure(app, mem, app.rules.find_one({"version": winner[0]["version"]}, {"_id": 0}), run["_id"])
        print(f"promoted {winner[0]['version']}; procedural memory updated")
    else:
        print(f"no candidate passed; {live['version']} stays live")

    terms = learn_terms(app, mem, run)
    app.learning_jobs.update_many({"run_id": run["_id"]}, {"$set": {"status": "done", "finished_at": _now()}})
    for t in terms:
        print(f"learned term: {t['printed_name']!r} -> {t['standard_name']} ({t['test_id']})")
    return {
        "baseline": {"version": live["version"], **_summary(baseline)},
        "candidates": [{"version": c["version"], "proposed_by": c["proposed_by"], "summary": c["summary"], **_summary(r),
                        "regressions": len(b), "passes": p} for c, r, b, p in results],
        "promoted": winner[0]["version"] if winner else None,
        "terms": terms,
    }


def main() -> int:
    try:
        result = learn()
    finally:
        get_db("HARNESS_AGENT").learning_jobs.update_many({"status": "started"}, {"$set": {"status": "done", "finished_at": _now()}})
    return 0 if result.get("promoted") else 1


if __name__ == "__main__":
    sys.exit(main())
