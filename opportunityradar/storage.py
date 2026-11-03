"""SQLite storage for one local profile and the demo catalog."""
import json
import time
from opportunityradar.duplicates import is_duplicate
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
        db.execute("CREATE TABLE IF NOT EXISTS discovered (id INTEGER PRIMARY KEY, payload TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS search_cache (query TEXT PRIMARY KEY, created REAL NOT NULL, payload TEXT NOT NULL)")
        db.execute("CREATE TABLE IF NOT EXISTS search_attempts (created REAL NOT NULL)")
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


def load_discovered(path=None):
    with connection(path) as db:
        return [json.loads(row[0]) for row in db.execute("SELECT payload FROM discovered ORDER BY id DESC")]


def save_discovered(records, path=None):
    with connection(path) as db:
        db.execute("BEGIN IMMEDIATE")
        existing = [json.loads(row[0]) for row in db.execute("SELECT payload FROM discovered")]
        added = 0
        for item in records:
            if item.get("is_demo") is not False or not item.get("source_url"):
                continue
            if not is_duplicate(item, existing):
                db.execute("INSERT INTO discovered (payload) VALUES (?)", (json.dumps(item),))
                existing.append(item)
                added += 1
        return added


def cached_search(query, path=None):
    with connection(path) as db:
        row = db.execute("SELECT payload FROM search_cache WHERE query = ? AND created > ?",
                         (query, time.time() - 900)).fetchone()
        return json.loads(row[0]) if row else None


def store_search(query, records, path=None):
    with connection(path) as db:
        db.execute("DELETE FROM search_cache WHERE created <= ?", (time.time() - 900,))
        db.execute("INSERT OR REPLACE INTO search_cache VALUES (?, ?, ?)",
                   (query, time.time(), json.dumps(records)))


def reserve_search(path=None):
    # Reserve before the API call, even for failed calls. Transaction prevents
    # concurrent sessions from exceeding the shared single-user allowance.
    with connection(path) as db:
        db.execute("BEGIN IMMEDIATE")
        db.execute("DELETE FROM search_attempts WHERE created <= ?", (time.time() - 3600,))
        if db.execute("SELECT COUNT(*) FROM search_attempts").fetchone()[0] >= 12:
            return False
        db.execute("INSERT INTO search_attempts VALUES (?)", (time.time(),))
        return True
