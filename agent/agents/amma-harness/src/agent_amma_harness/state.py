"""Agent state definition for Amma Harness."""

from __future__ import annotations

from typing import Annotated, TypedDict

from langchain_core.messages import AnyMessage
from langgraph.graph.message import add_messages


class HarnessState(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]
