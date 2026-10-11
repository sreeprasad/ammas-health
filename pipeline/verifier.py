"""Verifier step: check each read value against her trend and the printed range."""

import re
from datetime import datetime

from pymongo.database import Database

RULE_V3 = {"version": "v3", "min_confidence": 0.8, "max_jump": 0.5}


def parse_range(text: str) -> tuple[float | None, float | None]:
    numbers = [float(n) for n in re.findall(r"\d+(?:\.\d+)?", text)]
    if text.strip().startswith("<") and numbers:
        return None, numbers[0]
    if text.strip().startswith(">") and numbers:
        return numbers[0], None
    if len(numbers) >= 2:
        return numbers[0], numbers[1]
    return None, None


def known_aliases(db: Database) -> dict[str, str]:
    """Printed name (lower case) to standard test id, learned from verified history."""
    aliases = {}
    for row in db["values"].aggregate([
        {"$match": {"status": "verified", "test": {"$ne": None}}},
        {"$group": {"_id": {"$toLower": "$printed_name"}, "test": {"$first": "$test"}}},
    ]):
        aliases[row["_id"]] = row["test"]
    return aliases


def last_value(db: Database, test: str, before: datetime) -> float | None:
    row = db["values"].find_one(
        {"test": test, "status": "verified", "report_date": {"$lt": before}},
        sort=[("report_date", -1)],
    )
    return row["value"] if row else None


def verify(db: Database, reading: dict, report_date: datetime, rule: dict = RULE_V3) -> dict:
    aliases = known_aliases(db)
    results = []
    for v in reading["values"]:
        test = aliases.get(v["printed_name"].lower())
        checks = []
        status = "verified"

        previous = last_value(db, test, report_date) if test else None
        jump = abs(v["value"] - previous) / previous if (v["value"] is not None and previous) else None

        if test is None:
            checks.append("new term")
        if v["value"] is None:
            status = "needs_person"
            checks.append(f'unreadable "{v["value_text"]}"')
        elif v["confidence"] < rule["min_confidence"] and jump is not None and jump > rule["max_jump"]:
            status = "needs_person"
            checks.append(f"low confidence {v['confidence']:.2f} and {jump:.0%} jump from {previous:g}")
        elif jump is not None:
            checks.append("fits trend" if jump <= rule["max_jump"] else f"{jump:.0%} jump from {previous:g}, read clearly")

        low, high = parse_range(v["range_text"])
        if v["value"] is not None and (low is not None or high is not None):
            expected = "L" if low is not None and v["value"] < low else "H" if high is not None and v["value"] > high else ""
            if v["flag"] and expected != v["flag"]:
                checks.append(f"printed flag {v['flag']} disagrees with range")

        results.append({**v, "test": test, "previous": previous, "jump": None if jump is None else round(jump, 3),
                        "status": status, "checks": checks, "range": {"text": v["range_text"], "low": low, "high": high}})

    return {
        "rule": rule["version"],
        "values": results,
        "verified": sum(r["status"] == "verified" for r in results),
        "needs_person": sum(r["status"] == "needs_person" for r in results),
    }
