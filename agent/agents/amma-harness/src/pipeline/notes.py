"""Doctor notes with the note text encrypted client-side (explicit encryption, local master key).

The text is stored only as ciphertext; every reader goes through this module.
"""

import base64
import logging
import os

from bson.binary import STANDARD
from bson.codec_options import CodecOptions
from pymongo.database import Database
from pymongo.encryption import Algorithm, ClientEncryption
from pymongo.errors import ConfigurationError

log = logging.getLogger(__name__)

KEY_VAULT = "__keyvault"
KEY_NAME = "notes"
_cache: dict = {}


def _encryption(db: Database) -> ClientEncryption:
    if "ce" not in _cache:
        master = base64.b64decode(os.environ["NOTES_MASTER_KEY"])
        _cache["ce"] = ClientEncryption({"local": {"key": master}}, f"{db.name}.{KEY_VAULT}", db.client,
                                        CodecOptions(uuid_representation=STANDARD))
    return _cache["ce"]


def _key_id(db: Database):
    ce = _encryption(db)
    key = ce.get_key_by_alt_name(KEY_NAME)
    return key["_id"] if key else ce.create_data_key("local", key_alt_names=[KEY_NAME])


def encrypt(db: Database, text: str):
    return _encryption(db).encrypt(text, Algorithm.AEAD_AES_256_CBC_HMAC_SHA_512_Random, key_id=_key_id(db))


def _plain(db: Database, note: dict) -> dict:
    if "text_enc" in note:
        note = {**note, "text": _encryption(db).decrypt(note["text_enc"])}
        note.pop("text_enc")
    return note


def all_notes(db: Database) -> list[dict]:
    return [_plain(db, n) for n in db.notes.find({}, {"_id": 0}).sort("date", 1)]


def note_on(db: Database, day: str) -> dict | None:
    """The note for a visit, or None if there is none or this runtime cannot decrypt (no key or no libmongocrypt)."""
    note = db.notes.find_one({"date": day}, {"_id": 0})
    if not note:
        return None
    try:
        return _plain(db, note)
    except (KeyError, ConfigurationError) as e:
        log.warning("note for %s left encrypted: %s", day, e)
        return None


def store(db: Database, note: dict) -> None:
    doc = {k: v for k, v in note.items() if k != "text"}
    doc["text_enc"] = encrypt(db, note["text"])
    db.notes.replace_one({"note_id": note["note_id"]}, doc, upsert=True)
