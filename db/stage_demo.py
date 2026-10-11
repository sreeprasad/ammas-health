"""Put the demo in its starting state: Sep 12 uploaded, read, and paused on the smudged LDL."""

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import checkpoints, memory, replay, run  # noqa: E402
from pipeline.db import get_db  # noqa: E402

TRUTH = ROOT / "data" / "truth" / "2026-09-12_full-panel.json"


def main() -> None:
    db = get_db()
    print("reset:", replay.reset_uploads(db, memory.for_amma(session_id="stage")))
    truth = json.loads(TRUTH.read_text())
    report_id = replay.ingest_photos(db, [ROOT / "data" / p["file"] for p in truth["files"]["photos"]],
                                     "sreeprasad", truth["report_key"])
    run_id = checkpoints.start_run(db, report_id)["_id"]
    print(f"report {report_id} run {run_id}: {run.advance(db, run_id)}")


if __name__ == "__main__":
    main()
