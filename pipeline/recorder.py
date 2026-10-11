"""Record step: verified and pending values into the values collection; apply family answers."""

from datetime import datetime, timezone

from bson import ObjectId
from pymongo import UpdateOne
from pymongo.database import Database


def record_values(db: Database, report: dict, run_id: ObjectId, report_date: datetime, verification: dict) -> dict:
    now = datetime.now(timezone.utc)
    ops = []
    for v in verification["values"]:
        key = {"report_id": report["_id"], "page": v["page"], "printed_name": v["printed_name"]}
        doc = {
            **key,
            "run_id": run_id,
            "report_key": report.get("report_key"),
            "report_date": report_date,
            "test": v["test"],
            "value": v["value"],
            "value_text": v["value_text"],
            "unit": v["unit"],
            "range": v["range"],
            "flag": v["flag"],
            "box": v["box"],
            "confidence": v["confidence"],
            "status": v["status"],
            "checks": v["checks"],
            "source": "reader",
            "updated_at": now,
        }
        ops.append(UpdateOne(key, {"$set": doc, "$setOnInsert": {"created_at": now}}, upsert=True))
    if ops:
        db["values"].bulk_write(ops)
    pending = [row["_id"] for row in db["values"].find({"report_id": report["_id"], "status": "needs_person"}, {"_id": 1})]
    return {"written": len(ops), "pending_ids": pending}


def apply_answers(db: Database, run_id: ObjectId) -> list[dict]:
    """Apply unapplied answers for this run. Returns the answers applied now."""
    applied = []
    for answer in db.answers.find({"run_id": run_id, "applied": {"$ne": True}}).sort("at", 1):
        now = datetime.now(timezone.utc)
        db["values"].update_one(
            {"_id": answer["value_id"], "status": "needs_person"},
            {"$set": {"value": answer["value"], "value_text": str(answer["value"]).removesuffix(".0"),
                      "status": "verified", "source": "person", "answered_by": answer["member_id"],
                      "answered_at": answer["at"], "updated_at": now},
             "$push": {"checks": f"confirmed by {answer['member_id']}"}},
        )
        db.answers.update_one({"_id": answer["_id"]}, {"$set": {"applied": True, "applied_at": now}})
        applied.append(answer)
    return applied
