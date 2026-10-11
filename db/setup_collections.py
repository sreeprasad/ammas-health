from datetime import datetime, timezone

from pymongo import ASCENDING, DESCENDING, IndexModel

from atlas import APP_DB, client_for

COLLECTIONS = {
    "reports": [IndexModel([("report_date", DESCENDING)]), IndexModel([("file_hash", ASCENDING)], unique=True, sparse=True)],
    "values": [
        IndexModel([("test", ASCENDING), ("report_date", ASCENDING)]),
        IndexModel([("report_id", ASCENDING)]),
        IndexModel([("status", ASCENDING)]),
    ],
    "runs": [IndexModel([("report_id", ASCENDING)], unique=True), IndexModel([("status", ASCENDING), ("updated_at", DESCENDING)])],
    "answers": [IndexModel([("run_id", ASCENDING)])],
    "rules": [IndexModel([("version", ASCENDING)], unique=True), IndexModel([("live", ASCENDING)])],
    "followups": [IndexModel([("due", ASCENDING)]), IndexModel([("status", ASCENDING)])],
    "audit_log": [IndexModel([("at", DESCENDING)]), IndexModel([("event", ASCENDING)])],
    "members": [IndexModel([("member_id", ASCENDING)], unique=True)],
    "originals.files": [IndexModel([("filename", ASCENDING), ("uploadDate", ASCENDING)])],
    "originals.chunks": [IndexModel([("files_id", ASCENDING), ("n", ASCENDING)], unique=True)],
}

MEMBERS = [
    {"member_id": "sreeprasad", "name": "Sreeprasad", "relation": "son", "scope": "full"},
    {"member_id": "sister", "name": "Sister", "relation": "daughter", "scope": "full"},
    {"member_id": "aide", "name": "Home aide", "relation": "caregiver", "scope": "medications"},
]


def main() -> None:
    db = client_for("SETUP_ADMIN")[APP_DB]
    existing = set(db.list_collection_names())
    for name, indexes in COLLECTIONS.items():
        if name not in existing:
            db.create_collection(name)
        db[name].create_indexes(indexes)
        print(f"{name}: ready ({len(indexes)} indexes)")

    now = datetime.now(timezone.utc)
    for member in MEMBERS:
        db.members.update_one(
            {"member_id": member["member_id"]},
            {"$set": member, "$setOnInsert": {"created_at": now}},
            upsert=True,
        )
    for m in db.members.find({}, {"_id": 0, "member_id": 1, "scope": 1}).sort("member_id"):
        print(f"member {m['member_id']}: scope={m['scope']}")


if __name__ == "__main__":
    main()
