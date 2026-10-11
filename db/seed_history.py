"""Load the 22 older reports as verified history: originals in GridFS, reports and values docs.

Runs as harness_agent. Reads the generator's local truth files, never eval_vault.
"""

import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from gridfs import GridFSBucket

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.db import get_db  # noqa: E402

DATA = Path(__file__).resolve().parent.parent / "data"
LIVE = "2026-09-12"


def upload(bucket: GridFSBucket, path: Path, content_type: str, metadata: dict):
    with path.open("rb") as f:
        return bucket.upload_from_stream(path.name, f, metadata={**metadata, "contentType": content_type})


def main() -> None:
    db = get_db()
    bucket = GridFSBucket(db, bucket_name="originals")
    now = datetime.now(timezone.utc)

    for old in db.reports.find({"source": "seed"}, {"pages": 1, "pdf_file_id": 1}):
        for file_id in [p["file_id"] for p in old["pages"]] + [old["pdf_file_id"]]:
            bucket.delete(file_id)
    db.reports.delete_many({"source": "seed"})
    db["values"].delete_many({"source": "seed"})

    reports = values = 0
    for path in sorted((DATA / "truth").glob("*.json")):
        if LIVE in path.name:
            continue
        truth = json.loads(path.read_text())
        meta = {"report_key": truth["report_key"], "synthetic": True}
        pdf_id = upload(bucket, DATA / truth["files"]["pdf"], "application/pdf", meta)
        pages = [
            {"page": p["page"], "file_id": upload(bucket, DATA / p["file"], "image/jpeg", {**meta, "page": p["page"]}),
             "content_type": "image/jpeg"}
            for p in truth["files"]["photos"]
        ]
        report_date = datetime.fromisoformat(truth["visit_date"]).replace(tzinfo=timezone.utc)
        report_id = db.reports.insert_one({
            "report_key": truth["report_key"], "title": truth["title"], "report_date": report_date,
            "status": "seeded", "source": "seed", "synthetic": True, "pages": pages, "pdf_file_id": pdf_id,
            "uploaded_at": now,
        }).inserted_id
        db["values"].insert_many([
            {
                "report_id": report_id, "report_key": truth["report_key"], "report_date": report_date,
                "test": v["test"], "standard_name": v["standard_name"], "printed_name": v["printed_name"],
                "value": v["value"], "value_text": v["value_text"],
                "unit": v["unit"], "range": v["range"], "flag": v["flag"], "page": v["page"], "box": v["box"],
                "status": "verified", "source": "seed", "checks": [], "created_at": now, "updated_at": now,
            }
            for v in truth["values"]
        ])
        reports += 1
        values += len(truth["values"])
    db.notes.delete_many({})
    notes = [json.loads(p.read_text()) for p in sorted((DATA / "notes").glob("note-*.json"))]
    db.notes.insert_many([{**n, "created_at": now} for n in notes])
    db.notes.create_index("date")
    print(f"history: {reports} reports, {values} verified values, originals in GridFS, {len(notes)} doctor notes")


if __name__ == "__main__":
    main()
