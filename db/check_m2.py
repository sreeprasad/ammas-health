"""M2 check: upload the Sep 12 photos, expect 22 verified + 1 paused LDL, then kill and resume the worker.

Needs the web app running (npm run dev in web/, default http://localhost:3100).
"""

import json
import os
import signal
import subprocess
import sys
import time
from pathlib import Path

import requests
from bson import ObjectId
from gridfs import GridFSBucket

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from pipeline.db import get_db  # noqa: E402

WEB = os.environ.get("WEB_URL", "http://localhost:3100")
TRUTH = ROOT / "data" / "truth" / "2026-09-12_full-panel.json"
LOG = Path(os.environ.get("WORKER_LOG", "/tmp/amma-worker.log"))
results: list[tuple[bool, str]] = []


def check(ok: bool, message: str) -> None:
    results.append((ok, message))
    print(f"{'PASS' if ok else 'FAIL'} {message}")


def reset(db) -> None:
    bucket = GridFSBucket(db, bucket_name="originals")
    for report in db.reports.find({"source": "upload"}):
        for page in report["pages"]:
            bucket.delete(page["file_id"])
        db.runs.delete_many({"report_id": report["_id"]})
        db["values"].delete_many({"report_id": report["_id"]})
    db.reports.delete_many({"source": "upload"})
    db.answers.delete_many({})


def start_worker() -> subprocess.Popen:
    log = LOG.open("a")
    return subprocess.Popen([sys.executable, str(ROOT / "worker" / "run_worker.py")], stdout=log, stderr=log)


def wait_for(db, report_id, statuses: set[str], timeout: int) -> dict | None:
    deadline = time.time() + timeout
    while time.time() < deadline:
        run = db.runs.find_one({"report_id": report_id})
        if run and run["status"] in statuses:
            return run
        time.sleep(1)
    return db.runs.find_one({"report_id": report_id})


def main() -> int:
    db = get_db()
    reset(db)
    truth = json.loads(TRUTH.read_text())
    expected = {(v["page"], v["printed_name"]): v["value"] for v in truth["values"]}

    worker = start_worker()
    time.sleep(4)

    files = [("files", (Path(p["file"]).name, (ROOT / "data" / p["file"]).read_bytes(), "image/jpeg"))
             for p in truth["files"]["photos"]]
    response = requests.post(f"{WEB}/api/upload", files=files, headers={"x-member-id": "sreeprasad"},
                             data={"member_id": "sreeprasad", "report_key": truth["report_key"]}, timeout=60)
    check(response.status_code == 201, f"upload API -> {response.status_code}")
    report_id = ObjectId(response.json()["report_id"])

    started = time.time()
    run = wait_for(db, report_id, {"paused", "complete", "failed"}, timeout=240)
    check(run is not None and run["status"] == "paused", f"run paused after {time.time() - started:.0f}s "
          f"(status {run and run['status']}, error {run and run.get('error')})")
    if not run or run["status"] != "paused":
        worker.kill()
        return 1

    if os.environ.get("AGENT_INVOKE_URL"):
        deadline = time.time() + 60
        while time.time() < deadline and (db.runs.find_one({"_id": run["_id"]}).get("agent") or {}).get("status") != "suspended":
            time.sleep(1)
        agent = db.runs.find_one({"_id": run["_id"]}).get("agent") or {}
        check(agent.get("status") == "suspended", f"Agent Engine execution {agent.get('execution_id')} suspended")

    rows = list(db["values"].find({"report_id": report_id}))
    verified = [r for r in rows if r["status"] == "verified"]
    pending = [r for r in rows if r["status"] == "needs_person"]
    check(len(verified) == 22, f"{len(verified)} values verified (want 22)")
    check(len(pending) == 1 and pending[0]["printed_name"] == "LDL-C",
          f"paused on {[(r['printed_name'], r['value_text']) for r in pending]} (want LDL-C)")
    wrong = [(r["printed_name"], r["value"], expected.get((r["page"], r["printed_name"]))) for r in verified
             if expected.get((r["page"], r["printed_name"])) != r["value"]]
    check(not wrong, f"verified values match the synthetic truth (mismatches: {wrong})")

    worker.send_signal(signal.SIGKILL)
    worker.wait()
    check(True, "worker killed during the pause")

    answer = requests.post(f"{WEB}/api/answers", json={"run_id": str(run["_id"]), "value_id": str(pending[0]["_id"]),
                                                       "value": 104, "member_id": "sreeprasad"}, timeout=30)
    check(answer.status_code == 201, f"answer API -> {answer.status_code} while the worker is down")
    time.sleep(3)
    check(db.runs.find_one({"_id": run["_id"]})["status"] == "paused", "run still paused with no worker")

    worker = start_worker()
    run = wait_for(db, report_id, {"complete", "failed"}, timeout=120)
    deadline = time.time() + 60
    while os.environ.get("AGENT_INVOKE_URL") and time.time() < deadline \
            and (db.runs.find_one({"_id": run["_id"]}).get("agent") or {}).get("status") == "suspended":
        time.sleep(1)
    run = db.runs.find_one({"_id": run["_id"]})
    worker.send_signal(signal.SIGTERM)
    worker.wait()

    check(run["status"] == "complete", f"run complete after restart (status {run['status']})")
    if os.environ.get("AGENT_INVOKE_URL"):
        agent = run.get("agent") or {}
        check(agent.get("status") == "completed", f"Agent Engine execution {agent.get('execution_id')} {agent.get('status')}")
    check(run["executions"].get("read") == 1, f"Reader ran {run['executions'].get('read')} time(s) in total (want 1)")
    ldl = db["values"].find_one({"_id": pending[0]["_id"]})
    check(ldl["status"] == "verified" and ldl["value"] == 104 and ldl["source"] == "person",
          f"LDL now {ldl['status']} {ldl['value']} from {ldl['source']}")
    print("steps:", ", ".join(f"{s['name']} {s['duration_ms']}ms ({s['summary']})" for s in run["steps"]))
    print(f"worker log: {LOG}")
    return 0 if all(ok for ok, _ in results) else 1


if __name__ == "__main__":
    sys.exit(main())
