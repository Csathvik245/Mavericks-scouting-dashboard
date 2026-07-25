"""
Tiny TTL cache backed by SQLite.

The user requested MySQL caching but no MySQL server is installed on this
machine, so we use SQLite (bundled with Python, zero install). The schema and
access pattern are intentionally trivial (key -> JSON value + expiry), so the
backend can be pointed at MySQL later by swapping this one module. See README.
"""
import json
import sqlite3
import threading
import time

import config
from config import CACHE_DB

_lock = threading.Lock()


def _conn():
    c = sqlite3.connect(CACHE_DB, check_same_thread=False)
    c.execute(
        """CREATE TABLE IF NOT EXISTS cache (
               cache_key   TEXT PRIMARY KEY,
               value       TEXT NOT NULL,
               created_at  REAL NOT NULL,
               expires_at  REAL NOT NULL
           )"""
    )
    return c


def get(key):
    """Return the cached (deserialized) value, or None if missing/expired.

    In OFFLINE mode expiry is ignored: the committed cache.db is a static
    snapshot of a completed season, so a stored value is always served.
    """
    with _lock, _conn() as c:
        row = c.execute(
            "SELECT value, expires_at FROM cache WHERE cache_key = ?", (key,)
        ).fetchone()
        if not row:
            return None
        value, expires_at = row
        if not config.OFFLINE and expires_at < time.time():
            c.execute("DELETE FROM cache WHERE cache_key = ?", (key,))
            return None
        return json.loads(value)


def set(key, value, ttl):
    now = time.time()
    with _lock, _conn() as c:
        c.execute(
            "REPLACE INTO cache (cache_key, value, created_at, expires_at) "
            "VALUES (?, ?, ?, ?)",
            (key, json.dumps(value), now, now + ttl),
        )


def cached(key, ttl, producer):
    """Return cached value for `key`, else call producer(), store, return it.

    In OFFLINE mode we never call the producer (no live nba_api access): a miss
    raises, so a mis-seeded cache fails loudly instead of hanging on a network
    call that can't succeed from a datacenter IP.
    """
    hit = get(key)
    if hit is not None:
        return hit
    if config.OFFLINE:
        raise RuntimeError(
            f"OFFLINE cache miss for '{key}'. The committed cache.db is missing "
            f"this entry — re-run seed_cache.py and commit the refreshed cache.db."
        )
    value = producer()
    set(key, value, ttl)
    return value


def info():
    """Diagnostics: list cache keys with age/expiry for debugging."""
    now = time.time()
    with _lock, _conn() as c:
        rows = c.execute(
            "SELECT cache_key, created_at, expires_at FROM cache ORDER BY created_at"
        ).fetchall()
    return [
        {
            "key": k,
            "age_sec": round(now - created, 1),
            "expires_in_sec": round(exp - now, 1),
            "fresh": exp >= now,
        }
        for (k, created, exp) in rows
    ]


def clear():
    with _lock, _conn() as c:
        c.execute("DELETE FROM cache")
