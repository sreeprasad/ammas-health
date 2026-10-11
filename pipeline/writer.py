"""Memory writer: verified values only, into the four Agent Engine memory types.

Policy no-uncertain-writes: a value that is not verified is never written; the refusal is logged as HELD.
Every write is mirrored to the memory_writes collection so the UI can show writes by type.
"""

from datetime import datetime, timezone

from bson import ObjectId
from pymongo.database import Database

from agent_engine_sdk_memory import Memory

from pipeline.memory import LAB_DOMAIN, READING_PROCEDURE

POLICY = "no-uncertain-writes"


def _now() -> datetime:
    return datetime.now(timezone.utc)


def _log_write(db: Database, kind: str, key: str, summary: str, run_id: ObjectId | None) -> None:
    db.memory_writes.update_one(
        {"kind": kind, "key": key},
        {"$set": {"summary": summary, "run_id": run_id, "at": _now()}, "$inc": {"writes": 1}},
        upsert=True,
    )


def _audit(db: Database, event: str, actor: str, what: str, **extra) -> None:
    db.audit_log.insert_one({"at": _now(), "event": event, "actor": actor, "what": what, "policy": POLICY, **extra})


def standard_names(db: Database) -> dict[str, str]:
    return {row["_id"]: row["name"] for row in db["values"].aggregate([
        {"$match": {"standard_name": {"$exists": True}}},
        {"$group": {"_id": "$test", "name": {"$first": "$standard_name"}}},
    ])}


def _fact_text(value: dict, name: str, previous: dict | None) -> str:
    when = value["report_date"].date().isoformat()
    text = f"{name} was {value['value_text']} {value['unit']} on {when} (printed range {value['range']['text']}"
    text += f", flagged {value['flag']})." if value.get("flag") else ")."
    if previous:
        text += f" Before that: {previous['value_text']} on {previous['report_date'].date().isoformat()}."
    return text


def remember_fact(db: Database, mem: Memory, value: dict, names: dict[str, str], run_id: ObjectId | None) -> bool:
    """Semantic: one fact per test holding the current value. Older values stay in the values collection."""
    if value["status"] != "verified":
        raise ValueError(f"{POLICY}: refusing to write {value['printed_name']} with status {value['status']}")
    newer = db["values"].find_one({"test": value["test"], "status": "verified", "report_date": {"$gt": value["report_date"]}})
    if newer:
        return False
    previous = db["values"].find_one({"test": value["test"], "status": "verified", "report_date": {"$lt": value["report_date"]}},
                                     sort=[("report_date", -1)])
    name = names.get(value["test"], value["printed_name"])
    text = _fact_text(value, name, previous)
    mem.save_semantic(
        text=text,
        label=f"lab-{value['test']}",
        source="memory-writer",
        metadata={"test": value["test"], "value": value["value"], "unit": value["unit"],
                  "report_date": value["report_date"].isoformat(), "value_id": str(value["_id"])},
        upsert=True,
    )
    _log_write(db, "semantic", f"lab-{value['test']}", text, run_id)
    return True


def remember_term(db: Database, mem: Memory, printed_name: str, test: str, unit: str, names: dict[str, str],
                  run_id: ObjectId | None) -> bool:
    """Taxonomic: printed name -> standard name, shared across the project."""
    key = f"{LAB_DOMAIN}:{printed_name.lower()}"
    if db.memory_writes.find_one({"kind": "taxonomic", "key": key}):
        return False
    name = names.get(test, test)
    definition = f'"{printed_name}" on a lab report means {name} (test id {test}), reported in {unit or "no unit"}.'
    mem.save_taxonomic(domain=LAB_DOMAIN, term=printed_name, definition=definition, related_terms=[name, test],
                       metadata={"test": test})
    _log_write(db, "taxonomic", key, definition, run_id)
    return True


def remember_report_values(db: Database, mem: Memory, report_id: ObjectId, run_id: ObjectId | None,
                           actor: str = "Memory writer") -> dict:
    """Write every verified, not-yet-written value of a report; hold the rest."""
    names = standard_names(db)
    counts = {"semantic": 0, "taxonomic": 0, "held": 0, "released": 0, "older": 0}
    for value in db["values"].find({"report_id": report_id}).sort("page", 1):
        if value["status"] != "verified":
            if not value.get("held_at"):
                db["values"].update_one({"_id": value["_id"]}, {"$set": {"held_at": _now()}})
                _audit(db, "HELD", actor, f'{value["printed_name"]} "{value["value_text"]}" kept out of her record',
                       run_id=run_id, value_id=value["_id"])
            counts["held"] += 1
            continue
        if value.get("memory_written_at") or not value.get("test"):
            continue
        if remember_fact(db, mem, value, names, run_id):
            counts["semantic"] += 1
        else:
            counts["older"] += 1
        if remember_term(db, mem, value["printed_name"], value["test"], value["unit"], names, run_id):
            counts["taxonomic"] += 1
        db["values"].update_one({"_id": value["_id"]}, {"$set": {"memory_written_at": _now()}})
        if value.get("held_at"):
            counts["released"] += 1
            _audit(db, "RELEASED", value.get("answered_by", actor),
                   f'{value["printed_name"]} written after confirmation as "{value["value_text"]}"',
                   run_id=run_id, value_id=value["_id"])
    return counts


def remember_visit(db: Database, mem: Memory, visit_date: str, title: str, content: str, tags: list[str],
                   run_id: ObjectId | None) -> None:
    """Episodic: one episode per visit, stored under a per-visit session id."""
    if db.memory_writes.find_one({"kind": "episodic", "key": f"visit-{visit_date}"}):
        return
    mem.save_episode(title=title, content=content, session_id=f"visit-{visit_date}", tags=tags,
                     participants=["amma"], metadata={"visit_date": visit_date})
    _log_write(db, "episodic", f"visit-{visit_date}", title, run_id)


def remember_procedure(db: Database, mem: Memory, rule: dict, run_id: ObjectId | None) -> None:
    """Procedural: the reading rules for this report layout, one procedure per rule version."""
    key = f"{READING_PROCEDURE}-{rule['version']}"
    if db.memory_writes.find_one({"kind": "procedural", "key": key}):
        return
    content = (
        f"Reading rules {rule['version']} for Amrut Clinic lab reports. "
        f"Read every result row; write unreadable characters as '?'. "
        f"Ask a family member when a value is unreadable, or when confidence is below {rule['min_confidence']} "
        f"and the value jumps more than {rule['max_jump']:.0%} from her last verified value. "
        f"Never fill a digit from the trend."
    )
    mem.save_procedure(
        procedure=key,
        description=f"How to read and verify an Amrut Clinic lab report (rule {rule['version']})",
        content=content,
        trigger_conditions=["a new lab report photo or PDF arrives"],
        tags=["lab-report", rule["version"]],
        metadata={"rule_version": rule["version"]},
    )
    _log_write(db, "procedural", key, f"rule {rule['version']}", run_id)


def visit_content(db: Database, report_ids: list[ObjectId], note: dict | None) -> str:
    flagged = []
    for v in db["values"].find({"report_id": {"$in": report_ids}, "status": "verified", "flag": {"$in": ["H", "L"]}}):
        flagged.append(f"{v['printed_name']} {v['value_text']} {v['unit']} ({v['flag']})")
    total = db["values"].count_documents({"report_id": {"$in": report_ids}})
    parts = []
    if note:
        parts.append(f"{note['department']} note: {note['text']}")
    parts.append(f"{len(report_ids)} report(s), {total} values. Outside the printed range: "
                 + (", ".join(flagged) if flagged else "none") + ".")
    return " ".join(parts)
