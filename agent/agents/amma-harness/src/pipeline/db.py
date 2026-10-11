import os
from urllib.parse import quote_plus

from pymongo import MongoClient
from pymongo.database import Database

APP_DB = "amma_health"


def get_db(role: str = "HARNESS_AGENT") -> Database:
    user = quote_plus(os.environ[f"{role}_USER"])
    password = quote_plus(os.environ[f"{role}_PASSWORD"])
    host = os.environ["ATLAS_HOST"]
    client = MongoClient(
        f"mongodb+srv://{user}:{password}@{host}/?retryWrites=true&w=majority&appName=amma-harness",
        serverSelectionTimeoutMS=15000,
        tz_aware=True,
    )
    return client[APP_DB]
