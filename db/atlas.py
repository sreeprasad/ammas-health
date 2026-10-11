import os
from pathlib import Path
from urllib.parse import quote_plus

from dotenv import load_dotenv
from pymongo import MongoClient

load_dotenv(Path(__file__).resolve().parent.parent / ".env")

APP_DB = "amma_health"
VAULT_DB = "eval_vault"


def client_for(role: str) -> MongoClient:
    """role is the .env prefix: SETUP_ADMIN, HARNESS_AGENT or EVAL_RUNNER."""
    user = quote_plus(os.environ[f"{role}_USER"])
    password = quote_plus(os.environ[f"{role}_PASSWORD"])
    host = os.environ["ATLAS_HOST"]
    return MongoClient(
        f"mongodb+srv://{user}:{password}@{host}/?retryWrites=true&w=majority&appName=amma-health",
        serverSelectionTimeoutMS=15000,
    )
