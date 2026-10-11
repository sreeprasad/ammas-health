"""Reset uploaded reports so a run can be replayed, and put memory facts back to the latest remaining values."""

from datetime import datetime, timezone
from pathlib import Path

from agent_engine_sdk_memory import Memory
from bson import ObjectId
from gridfs import GridFSBucket
from pymongo.database import Database

from pipeline import writer


def reset_uploads(db: Database, mem: Memory) -> dict:
    bucket = GridFSBucket(db, bucket_name="originals")
    touched_tests = set()
    reports = list(db.reports.find({"source": "upload"}))
    for report in reports:
        for page in report["pages"]:
            bucket.delete(page["file_id"])
        touched_tests.update(t for t in db["values"].distinct("test", {"report_id": report["_id"]}) if t)
        db.runs.delete_many({"report_id": report["_id"]})
        db["values"].delete_many({"report_id": report["_id"]})
    db.reports.delete_many({"source": "upload"})
    db.answers.delete_many({})

    names = writer.standard_names(db)
    restored = 0
    for test in touched_tests:
        latest = db["values"].find_one({"test": test, "status": "verified"}, sort=[("report_date", -1)])
        if latest and writer.remember_fact(db, mem, latest, names, run_id=None):
            restored += 1
    return {"reports_removed": len(reports), "facts_restored": restored}


def ingest_photos(db: Database, photos: list[Path], member_id: str, report_key: str | None) -> ObjectId:
    """Same effect as the web upload route: pages into GridFS, then an uploaded report."""
    bucket = GridFSBucket(db, bucket_name="originals")
    pages = []
    for number, path in enumerate(photos, start=1):
        with path.open("rb") as f:
            file_id = bucket.upload_from_stream(path.name, f, metadata={
                "report_key": report_key, "page": number, "contentType": "image/jpeg", "uploaded_by": member_id})
        pages.append({"page": number, "file_id": file_id, "content_type": "image/jpeg"})
    now = datetime.now(timezone.utc)
    report_id = db.reports.insert_one({"report_key": report_key, "status": "uploaded", "source": "upload",
                                       "pages": pages, "uploaded_by": member_id, "uploaded_at": now}).inserted_id
    db.audit_log.insert_one({"at": now, "event": "UPLOADED", "actor": member_id,
                             "what": f"{len(pages)} page report uploaded", "report_id": report_id})
    return report_id
