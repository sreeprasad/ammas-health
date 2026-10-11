"""History search for the UI: memory retrieval (Voyage, hybrid) fused with Atlas Search over values."""

from agent_engine_sdk_memory import Memory
from pymongo.database import Database

VALUES_INDEX = "values_text"


def tests_from_memory(mem: Memory, query: str) -> list[str]:
    tests = []
    for chunk in mem.search(query, sources=["taxonomic", "semantic"], top_k=8):
        test = (chunk.metadata or {}).get("metadata", {}).get("test")
        if test and test not in tests:
            tests.append(test)
    return tests


def search_history(db: Database, mem: Memory, query: str, limit: int = 3) -> list[dict]:
    """Rank tests for a query and return each test's verified history, newest first."""
    memory_tests = tests_from_memory(mem, query)
    fused = db["values"].aggregate([
        {"$rankFusion": {
            "input": {"pipelines": {
                "text": [
                    {"$search": {"index": VALUES_INDEX, "text": {
                        "query": query, "path": ["printed_name", "standard_name", "test"], "fuzzy": {"maxEdits": 1}}}},
                    {"$limit": 50},
                ],
                "memory": [
                    {"$search": {"index": VALUES_INDEX, "compound": {"should": [
                        {"equals": {"path": "test", "value": test, "score": {"boost": {"value": len(memory_tests) - i}}}}
                        for i, test in enumerate(memory_tests)
                    ] or [{"equals": {"path": "test", "value": "__none__"}}]}}},
                    {"$limit": 50},
                ],
            }},
            "combination": {"weights": {"text": 1, "memory": 2}},
        }},
        {"$match": {"status": "verified", "test": {"$ne": None}}},
        {"$group": {"_id": "$test", "score": {"$max": {"$meta": "score"}}}},
        {"$sort": {"score": -1}},
        {"$limit": limit},
    ])
    results = []
    for row in fused:
        history = list(db["values"].find(
            {"test": row["_id"], "status": "verified"},
            {"_id": 0, "report_date": 1, "value": 1, "value_text": 1, "unit": 1, "printed_name": 1, "flag": 1},
        ).sort("report_date", 1))
        name = db["values"].find_one({"test": row["_id"], "standard_name": {"$exists": True}}, {"standard_name": 1})
        results.append({"test": row["_id"], "name": name["standard_name"] if name else row["_id"],
                        "from_memory": row["_id"] in memory_tests, "history": history})
    return results
