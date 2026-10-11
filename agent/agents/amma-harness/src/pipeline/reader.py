"""Reader step: report page images to structured values with Gemini vision."""

import hashlib
import os
from datetime import datetime, timezone

from bson import ObjectId
from gridfs import GridFSBucket
from google import genai
from google.genai import types
from pydantic import BaseModel
from pymongo.database import Database

READER_VERSION = "reader-v1"
DEFAULT_MODEL = "gemini-3.8-flash"

PROMPT = """This is a photo of one page of a lab report. Extract every test result row in the table.

For each row return:
- printed_name: the test name exactly as printed.
- value_text: the result exactly as you can see it. Replace any character you cannot read with "?".
  Never fill in an unreadable character from context, trends or the reference range.
- value: the result as a number, or null if any character is unreadable.
- unit, range_text and flag (H, L or empty) as printed on that row.
- box_2d: the box around the result value, as [ymin, xmin, ymax, xmax] scaled 0-1000.
- confidence: from 0 to 1, how sure you are that value_text is exactly what is printed.

Also return the page's collected date as YYYY-MM-DD, the report title and the page number."""


class ReadValue(BaseModel):
    printed_name: str
    value_text: str
    value: float | None
    unit: str
    range_text: str
    flag: str
    box_2d: list[int]
    confidence: float


class PageRead(BaseModel):
    collected_date: str | None
    report_title: str | None
    page_number: int | None
    values: list[ReadValue]


def _client() -> genai.Client:
    return genai.Client(api_key=os.environ["GEMINI_API_KEY"])


def _model() -> str:
    return os.environ.get("GEMINI_MODEL", DEFAULT_MODEL)


def read_page(image: bytes, mime_type: str, client: genai.Client | None = None) -> PageRead:
    client = client or _client()
    response = client.models.generate_content(
        model=_model(),
        contents=[types.Part.from_bytes(data=image, mime_type=mime_type), PROMPT],
        config=types.GenerateContentConfig(
            temperature=0,
            response_mime_type="application/json",
            response_schema=PageRead,
        ),
    )
    return PageRead.model_validate_json(response.text)


def _normalized_box(box_2d: list[int]) -> list[float] | None:
    if len(box_2d) != 4:
        return None
    ymin, xmin, ymax, xmax = box_2d
    return [round(xmin / 1000, 4), round(ymin / 1000, 4), round(xmax / 1000, 4), round(ymax / 1000, 4)]


def read_report(db: Database, report_id: ObjectId) -> dict:
    """Read every page of a report. Page readings are cached by image hash, model and reader version."""
    report = db.reports.find_one({"_id": report_id})
    bucket = GridFSBucket(db, bucket_name="originals")
    client = None
    model = _model()
    values, dates, titles, page_titles = [], [], [], {}
    gemini_calls = cache_hits = 0

    for page in sorted(report["pages"], key=lambda p: p["page"]):
        image = bucket.open_download_stream(page["file_id"]).read()
        digest = hashlib.sha256(image).hexdigest()
        cache_key = {"sha256": digest, "model": model, "reader_version": READER_VERSION}
        cached = db.reader_cache.find_one(cache_key)
        if cached:
            reading = PageRead.model_validate(cached["reading"])
            cache_hits += 1
        else:
            client = client or _client()
            reading = read_page(image, page.get("content_type", "image/jpeg"), client)
            gemini_calls += 1
            db.reader_cache.insert_one({**cache_key, "reading": reading.model_dump(), "created_at": datetime.now(timezone.utc)})

        if reading.collected_date:
            dates.append(reading.collected_date)
        if reading.report_title:
            titles.append(reading.report_title)
            page_titles[str(page["page"])] = reading.report_title
        for v in reading.values:
            values.append({
                "printed_name": v.printed_name.strip(),
                "value_text": v.value_text.strip(),
                "value": None if "?" in v.value_text else v.value,
                "unit": v.unit.strip(),
                "range_text": v.range_text.strip(),
                "flag": v.flag.strip().upper(),
                "page": page["page"],
                "box": _normalized_box(v.box_2d),
                "confidence": round(v.confidence, 3),
            })

    return {
        "model": model,
        "reader_version": READER_VERSION,
        "collected_date": max(set(dates), key=dates.count) if dates else None,
        "titles": sorted(set(titles)),
        "page_titles": page_titles,
        "values": values,
        "gemini_calls": gemini_calls,
        "cache_hits": cache_hits,
    }
