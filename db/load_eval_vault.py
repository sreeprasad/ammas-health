import json
import sys
from datetime import datetime, timezone
from pathlib import Path

from atlas import VAULT_DB, client_for

EXPECTED_REPORTS = 22


def main(truth_dir: Path, live_report: str) -> None:
    files = sorted(p for p in truth_dir.glob("*.json") if live_report not in p.name)
    if len(files) != EXPECTED_REPORTS:
        sys.exit(f"expected {EXPECTED_REPORTS} truth files excluding '{live_report}', found {len(files)} in {truth_dir}")

    answers = client_for("SETUP_ADMIN")[VAULT_DB].answers
    answers.create_index("report_key", unique=True)
    now = datetime.now(timezone.utc)
    total_values = 0
    for path in files:
        truth = json.loads(path.read_text())
        values = truth["values"] if isinstance(truth, dict) else truth
        total_values += len(values)
        answers.replace_one(
            {"report_key": path.stem},
            {"report_key": path.stem, "source_file": path.name, "truth": truth, "value_count": len(values), "loaded_at": now},
            upsert=True,
        )
    print(f"eval_vault.answers: {answers.count_documents({})} reports, {total_values} values")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit("usage: python load_eval_vault.py <truth_dir> <live_report_substring, e.g. 2026-09-12>")
    main(Path(sys.argv[1]), sys.argv[2])
