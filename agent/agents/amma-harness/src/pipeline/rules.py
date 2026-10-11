"""Reading rules as versioned data. One decide() is used by the live Verifier and by the eval runner."""

from datetime import datetime, timezone

from pymongo.database import Database

RULE_V3 = {
    "version": "v3",
    "summary": "Ask when a value is unreadable, or when confidence is low and the value jumps from her trend.",
    "doubt_unreadable": True,
    "doubt_below_confidence": 0.8,
    "doubt_requires_jump": True,
    "max_jump": 0.5,
    "on_doubt": "ask",
}

PARAM_KEYS = ["doubt_unreadable", "doubt_below_confidence", "doubt_requires_jump", "max_jump", "on_doubt"]


def decide(rule: dict, value: float | None, confidence: float, previous: float | None) -> tuple[str, float | None, str]:
    """Return (decision, final value, reason). Decisions: accept, ask, snap."""
    jump = abs(value - previous) / previous if (value is not None and previous) else None
    unreadable = value is None
    low = confidence < rule["doubt_below_confidence"]
    jumped = jump is not None and jump > rule["max_jump"]

    doubt = None
    if unreadable and rule["doubt_unreadable"]:
        doubt = "unreadable"
    elif low and (jumped or not rule["doubt_requires_jump"]):
        doubt = f"low confidence {confidence:.2f}" + (f" and {jump:.0%} jump from {previous:g}" if jumped else "")

    if doubt is None:
        if unreadable:
            return "ask", None, "unreadable"
        return "accept", value, "fits trend" if jump is not None and not jumped else "read clearly"
    if rule["on_doubt"] == "snap_to_trend" and previous is not None:
        return "snap", previous, f"{doubt}; snapped to trend {previous:g}"
    return "ask", None, doubt


def ensure_seeded(db: Database) -> None:
    if not db.rules.find_one({"version": RULE_V3["version"]}):
        db.rules.insert_one({**RULE_V3, "status": "live", "proposed_by": "system", "created_at": datetime.now(timezone.utc)})


def live_rule(db: Database) -> dict:
    ensure_seeded(db)
    return db.rules.find_one({"status": "live"}, {"_id": 0})
