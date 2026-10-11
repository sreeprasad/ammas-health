"""Amma's Health harness on Atlas Agent Engine: runs the report pipeline and pauses for a person."""

from __future__ import annotations

import json
import logging
import re
from datetime import datetime, timezone

from bson import ObjectId
from dotenv import load_dotenv
from langchain_core.messages import AIMessage
from langgraph.graph import END, START, StateGraph
from langgraph.graph.state import CompiledStateGraph
from langgraph.types import interrupt
from agent_engine_sdk_langgraph import App

from agent_amma_harness.state import HarnessState
from agent_amma_harness.tools import register
from pipeline import checkpoints, run
from pipeline.db import get_db

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)-8s | %(message)s")
logger = logging.getLogger(__name__)
load_dotenv()

app = App(app_name="Amma Harness")

register(app)

REPORT_ID = re.compile(r"\b[0-9a-f]{24}\b")
ANSWER_SCHEMA = {
    "type": "object",
    "required": ["value"],
    "properties": {"value": {"type": "number"}, "reviewer_notes": {"type": "string"}},
    "additionalProperties": False,
}
NUMBER = re.compile(r"-?\d+(?:\.\d+)?")


def _text(message) -> str:
    content = message.content
    return content if isinstance(content, str) else json.dumps(content)


def _answer_value(answer) -> float | None:
    """The resume payload may be a bare value or a review decision with notes; take the first number in it."""
    match = NUMBER.search(answer if isinstance(answer, str) else json.dumps(answer))
    return float(match.group()) if match else None


@app.entrypoint
def build_agent() -> CompiledStateGraph:
    logger.info("Building Amma Harness graph")

    def process_report(state: HarnessState) -> dict:
        match = REPORT_ID.search(_text(state["messages"][-1]))
        if not match:
            return {"messages": [AIMessage(content="Send the id of an uploaded report to process it.")]}

        db = get_db()
        existing = checkpoints.start_run(db, ObjectId(match.group()))
        run_id = existing["_id"]
        # On resume, Agent Engine replays this node from the top. A paused run goes straight back to
        # interrupt(): advancing first would write memory inside the suspended step and conflict with it.
        status = "paused" if existing["status"] == "paused" else run.advance(db, run_id)

        if status == "paused":
            value = db["values"].find_one({"run_id": run_id, "status": "needs_person"})
            answer = interrupt({
                "reason": "A value could not be read with confidence. It is held out of her record until a person checks it.",
                "run_id": str(run_id),
                "value_id": str(value["_id"]),
                "printed_name": value["printed_name"],
                "read_as": value["value_text"],
                "page": value["page"],
                "range": value["range"]["text"],
                "question": f'What does {value["printed_name"]} read on page {value["page"]} of the paper report?',
                "response_schema": ANSWER_SCHEMA,
            })
            confirmed = _answer_value(answer)
            if confirmed is None:
                return {"messages": [AIMessage(content=f"No number in the answer {answer!r}; the value stays held.")]}
            db.answers.insert_one({"run_id": run_id, "value_id": value["_id"], "value": confirmed,
                                   "member_id": "family", "at": datetime.now(timezone.utc), "applied": False,
                                   "via": "agent-engine-resume"})
            status = run.advance(db, run_id)

        steps = [s["summary"] for s in checkpoints.load_run(db, run_id)["steps"]]
        return {"messages": [AIMessage(content=json.dumps({"run_id": str(run_id), "status": status, "steps": steps}))]}

    builder = StateGraph(HarnessState)
    builder.add_node("process_report", process_report)
    builder.add_edge(START, "process_report")
    builder.add_edge("process_report", END)
    return builder.compile(checkpointer=app.checkpointer())


def main() -> None:
    app.run()


if __name__ == "__main__":
    main()
