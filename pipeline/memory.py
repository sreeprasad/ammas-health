"""Standalone Agent Engine memory, always bound to Amma's record."""

import os

from agent_engine_sdk_memory import Memory, MemoryRequestContext

USER_ID = "amma"
LAB_DOMAIN = "lab-tests"
READING_PROCEDURE = "read-lab-report"


def client() -> Memory:
    """Local dev reaches the stack started by `agentengine dev up`; hosted needs a token and project id."""
    token = os.environ.get("AGENTIC_MEMORY_SERVICE_ACCOUNT_TOKEN")
    if token:
        return Memory(service_account_token=token, project_id=os.environ["AGENTIC_MEMORY_PROJECT_ID"])
    return Memory(base_url=os.environ["AGENTIC_MEMORY_BASE_URL"])


def for_amma(session_id: str | None = None) -> Memory:
    return client().bind(MemoryRequestContext(user_id=USER_ID, session_id=session_id))
