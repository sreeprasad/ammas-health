from pathlib import Path

from dotenv import load_dotenv

for _parent in reversed(Path(__file__).resolve().parents):
    if (_parent / ".env").is_file():
        load_dotenv(_parent / ".env")
