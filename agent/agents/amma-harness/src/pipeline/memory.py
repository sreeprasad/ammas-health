"""Standalone Agent Engine memory, always bound to Amma's record, locally and in the cloud."""

import os
import time

import requests
from agent_engine_sdk_memory import Memory, MemoryRequestContext

USER_ID = "amma"
LAB_DOMAIN = "lab-tests"
READING_PROCEDURE = "read-lab-report"
TOKEN_URL = "https://agentengine.mongodb.com/api/v1/oauth/token"

_token: dict = {"value": None, "expires_at": 0.0}


def _service_account_token() -> str:
    """Exchange the service account's client credentials for a 1-hour token, reused until near expiry."""
    if _token["value"] and time.time() < _token["expires_at"] - 120:
        return _token["value"]
    response = requests.post(
        TOKEN_URL,
        auth=(os.environ["AGENTIC_MEMORY_CLIENT_ID"], os.environ["AGENTIC_MEMORY_CLIENT_SECRET"]),
        data={"grant_type": "client_credentials"},
        timeout=30,
    )
    response.raise_for_status()
    body = response.json()
    _token.update(value=body["access_token"], expires_at=time.time() + float(body.get("expires_in", 3600)))
    return _token["value"]


def client() -> Memory:
    """AMMA_MEMORY_MODE=local reaches the stack from `agentengine dev up`; hosted uses a service account and the project id."""
    if os.environ.get("AMMA_MEMORY_MODE", "local") == "local":
        return Memory(base_url=os.environ["AGENTIC_MEMORY_BASE_URL"])
    return Memory(service_account_token=_service_account_token(), project_id=os.environ["AGENTIC_MEMORY_PROJECT_ID"])


def for_amma(session_id: str | None = None) -> Memory:
    return client().bind(MemoryRequestContext(user_id=USER_ID, session_id=session_id))
