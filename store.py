"""SQLite state: every article is fetched and translated exactly once."""
from __future__ import annotations

import os
import sqlite3
import time

from common import PROJECT_DIR

DB_PATH = os.path.join(PROJECT_DIR, "state.db")

SCHEMA = """
CREATE TABLE IF NOT EXISTS items (
    guid       TEXT PRIMARY KEY,
    link       TEXT NOT NULL,
    source     TEXT,
    category   TEXT,
    image      TEXT,
    pubdate    TEXT,
    title_de   TEXT,
    teaser_de  TEXT,
    body_de    TEXT,
    title_vi   TEXT,
    teaser_vi  TEXT,
    body_vi    TEXT,
    full_text  INTEGER DEFAULT 0,   -- 1 when the paid body was available
    first_seen REAL
);
CREATE INDEX IF NOT EXISTS idx_pubdate ON items(pubdate DESC);
"""


def connect() -> sqlite3.Connection:
    con = sqlite3.connect(DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def known_guids(con) -> set[str]:
    return {r[0] for r in con.execute("SELECT guid FROM items")}


def insert_translated(con, item: dict) -> None:
    con.execute(
        """INSERT OR REPLACE INTO items
           (guid, link, source, category, image, pubdate, title_de, teaser_de,
            body_de, title_vi, teaser_vi, body_vi, full_text, first_seen)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (
            item["guid"], item["link"], item.get("source"), item.get("category"),
            item.get("image"),
            item["pubdate"].isoformat() if item.get("pubdate") else None,
            item.get("title_de"), item.get("teaser_de"), item.get("body_de", ""),
            item.get("title_vi"), item.get("teaser_vi"), item.get("body_vi", ""),
            1 if item.get("body_de") else 0, time.time(),
        ),
    )
    con.commit()


def recent(con, limit: int) -> list[sqlite3.Row]:
    return list(
        con.execute(
            "SELECT * FROM items WHERE title_vi IS NOT NULL "
            "ORDER BY COALESCE(pubdate,'') DESC LIMIT ?",
            (limit,),
        )
    )
