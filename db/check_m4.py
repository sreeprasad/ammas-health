"""M4 check: stage the paused Sep 12 run, start the worker, then confirm LDL in a real browser and time the UI.

Needs the web app running (npm run dev in web/). With AGENT_INVOKE_URL set, the run goes through Agent Engine.
"""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline import memory, replay  # noqa: E402
from pipeline.db import get_db  # noqa: E402

TRUTH = ROOT / "data" / "truth" / "2026-09-12_full-panel.json"
SHOTS = Path(os.environ.get("SHOTS", "/tmp"))
LOG = Path(os.environ.get("WORKER_LOG", "/tmp/amma-worker.log"))


def stage(db, use_agent: bool):
    print("reset:", replay.reset_uploads(db, memory.for_amma(session_id="check-m4")))
    truth = json.loads(TRUTH.read_text())
    report_id = replay.ingest_photos(db, [ROOT / "data" / p["file"] for p in truth["files"]["photos"]],
                                     "sreeprasad", truth["report_key"])
    deadline = time.time() + 300
    while time.time() < deadline:
        doc = db.runs.find_one({"report_id": report_id}) or {}
        if use_agent and (doc.get("agent") or {}).get("status") == "suspended":
            return "paused (agent suspended)"
        if not use_agent and doc.get("status") == "paused":
            return "paused"
        time.sleep(1)
    return "timeout"


def main() -> int:
    db = get_db()
    use_agent = bool(os.environ.get("AGENT_INVOKE_URL"))
    log = LOG.open("a")
    worker = subprocess.Popen([sys.executable, str(ROOT / "worker" / "run_worker.py")], stdout=log, stderr=log)
    try:
        time.sleep(3)
        status = stage(db, use_agent)
        print(f"staged: {status} ({'Agent Engine' if use_agent else 'plain worker'})")
        ui = subprocess.run(["node", "scripts/check-m4.mjs"], cwd=ROOT / "web", env={**os.environ, "SHOTS": str(SHOTS)},
                            capture_output=True, text=True)
        print(ui.stdout or ui.stderr)
        time.sleep(5)
        ldl = db["values"].find_one({"printed_name": "LDL-C", "report_id": db.reports.find_one({"source": "upload"})["_id"]})
        print(f"LDL in Atlas: {ldl['status']} {ldl['value']} from {ldl['source']}")
        return ui.returncode
    finally:
        worker.send_signal(signal.SIGTERM)
        worker.wait()


if __name__ == "__main__":
    sys.exit(main())
