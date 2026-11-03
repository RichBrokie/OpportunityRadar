"""SQLite storage for one local profile and the demo catalog."""
import json
import os
import sqlite3
from contextlib import contextmanager
from pathlib import Path
from opportunityradar.catalog import demo_opportunities


@contextmanager
def connection(path=None):
    path = Path(path or os.getenv("OPPORTUNITYRADAR_DB", "data/radar.sqlite3"))
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    try:
        with db:
            yield db
    finally:
        db.close()


def initialize(path=None):
    with connection(path) as db:
        db.execute("CREATE TABLE IF NOT EXISTS profile (id INTEGER PRIMARY KEY CHECK(id = 1), payload TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS opportunities (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)")
        db.executemany("INSERT OR IGNORE INTO opportunities VALUES (?, ?)",
                       [(item["id"], json.dumps(item)) for item in demo_opportunities()])


def load_profile(path=None):
    with connection(path) as db:
        row = db.execute("SELECT payload FROM profile WHERE id = 1").fetchone()
    return json.loads(row[0]) if row else None


def save_profile(profile, path=None):
    if not profile["country"].strip():
        raise ValueError("Please enter your country.")
    with connection(path) as db:
        db.execute("INSERT INTO profile VALUES (1, ?) ON CONFLICT(id) DO UPDATE SET payload=excluded.payload", (json.dumps(profile),))


def load_opportunities(path=None):
    with connection(path) as db:
        return [json.loads(row[0]) for row in db.execute("SELECT payload FROM opportunities ORDER BY id")]
