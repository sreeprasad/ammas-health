import sys
import time
from pathlib import Path

from pymongo.operations import SearchIndexModel

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from pipeline.db import get_db  # noqa: E402
from pipeline.search import VALUES_INDEX  # noqa: E402

DEFINITION = {
    "mappings": {
        "dynamic": False,
        "fields": {
            "printed_name": {"type": "string"},
            "standard_name": {"type": "string"},
            "test": [{"type": "string"}, {"type": "token"}],
        },
    }
}


def main() -> None:
    values = get_db()["values"]
    existing = {i["name"]: i for i in values.list_search_indexes()}
    if VALUES_INDEX in existing:
        values.update_search_index(VALUES_INDEX, DEFINITION)
    else:
        values.create_search_index(SearchIndexModel(definition=DEFINITION, name=VALUES_INDEX))
    for _ in range(120):
        index = next(iter(values.list_search_indexes(VALUES_INDEX)), {})
        if index.get("queryable"):
            print(f"{VALUES_INDEX}: queryable ({index.get('status')})")
            return
        time.sleep(5)
    sys.exit(f"{VALUES_INDEX}: not queryable after 10 minutes")


if __name__ == "__main__":
    main()
