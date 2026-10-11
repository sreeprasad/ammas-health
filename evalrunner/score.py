"""Score reading rules on the 22 older reports against the locked answers in eval_vault.

Runs as the eval_runner database user, the only user that can read eval_vault.
"""

import re

from pymongo.database import Database

from pipeline import reader
from pipeline.rules import decide

TOLERANCE = 1e-6


def _key(printed_name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", printed_name.lower())


def build_cases(app_db: Database, vault_db: Database) -> list[dict]:
    """One case per locked answer: what the Reader saw, her previous value, and the true value."""
    history: dict[str, list] = {}
    for v in app_db["values"].find({"status": "verified", "source": "seed"}, {"test": 1, "report_date": 1, "value": 1}):
        history.setdefault(v["test"], []).append((v["report_date"], v["value"]))
    for rows in history.values():
        rows.sort()

    def previous_value(test: str, before) -> float | None:
        earlier = [value for when, value in history.get(test, []) if when < before]
        return earlier[-1] if earlier else None

    cases = []
    for answer in vault_db.answers.find({}, {"_id": 0}).sort("report_key", 1):
        truth = answer["truth"]
        report = app_db.reports.find_one({"report_key": answer["report_key"], "source": "seed"})
        reading = reader.read_report(app_db, report["_id"])
        seen = {(v["page"], _key(v["printed_name"])): v for v in reading["values"]}
        by_page = {}
        for v in reading["values"]:
            by_page.setdefault(v["page"], []).append(v)
        truth_rows = {}
        for t in truth["values"]:
            truth_rows.setdefault(t["page"], []).append(t)
        for t in truth["values"]:
            read = seen.get((t["page"], _key(t["printed_name"])))
            rows, truths = by_page.get(t["page"], []), truth_rows[t["page"]]
            matched_by = "name"
            if read is None and len(rows) == len(truths):
                read, matched_by = rows[truths.index(t)], "row order"
            cases.append({
                "report_key": answer["report_key"],
                "page": t["page"],
                "printed_name": t["printed_name"],
                "truth": t["value"],
                "read": read["value"] if read else None,
                "read_text": read["value_text"] if read else None,
                "confidence": read["confidence"] if read else 0.0,
                "found": read is not None,
                "matched_by": matched_by if read is not None else None,
                "previous": previous_value(t["test"], report["report_date"]),
            })
    return cases


def score(rule: dict, cases: list[dict]) -> dict:
    outcomes = []
    for c in cases:
        decision, final, reason = decide(rule, c["read"], c["confidence"], c["previous"])
        if decision == "ask":
            final = c["truth"]
        correct = final is not None and abs(final - c["truth"]) <= TOLERANCE * max(1.0, abs(c["truth"]))
        outcomes.append({**c, "decision": decision, "final": final, "correct": correct, "reason": reason})
    return {
        "version": rule["version"],
        "total": len(outcomes),
        "correct": sum(o["correct"] for o in outcomes),
        "asked": sum(o["decision"] == "ask" for o in outcomes),
        "snapped": sum(o["decision"] == "snap" for o in outcomes),
        "outcomes": outcomes,
    }


def regressions(baseline: dict, candidate: dict) -> list[dict]:
    """Values the baseline got right that the candidate gets wrong."""
    return [c for b, c in zip(baseline["outcomes"], candidate["outcomes"]) if b["correct"] and not c["correct"]]
