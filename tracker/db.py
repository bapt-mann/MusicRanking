"""Stockage local des ecoutes (SQLite). Schema = contrat partage avec le
futur backend social : on envoie exactement ces champs plus tard."""
from __future__ import annotations
import sqlite3

from . import config

SCHEMA = """
CREATE TABLE IF NOT EXISTS plays (
  id          INTEGER PRIMARY KEY AUTOINCREMENT,
  user_id     TEXT NOT NULL,
  device_id   TEXT NOT NULL,
  source      TEXT NOT NULL,
  title_raw   TEXT,
  artist_raw  TEXT,
  album_raw   TEXT,
  track_key   TEXT NOT NULL,
  duration_ms INTEGER,
  listened_ms INTEGER,
  percent     REAL,
  completed   INTEGER,
  started_at  TEXT,
  ended_at    TEXT
);
CREATE INDEX IF NOT EXISTS idx_plays_user_key ON plays(user_id, track_key);
"""


def connect():
    con = sqlite3.connect(config.DB_PATH)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


def insert_play(con, cfg, play):
    con.execute(
        """INSERT INTO plays(user_id, device_id, source, title_raw, artist_raw,
             album_raw, track_key, duration_ms, listened_ms, percent, completed,
             started_at, ended_at)
           VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?)""",
        (cfg["user_id"], cfg["device_id"], "spotify",
         play["title_raw"], play["artist_raw"], play["album_raw"], play["track_key"],
         play["duration_ms"], play["listened_ms"], play["percent"], play["completed"],
         play["started_at"], play["ended_at"]),
    )
    con.commit()


def fetch_plays(con, user_id):
    return list(con.execute(
        "SELECT * FROM plays WHERE user_id=? ORDER BY started_at", (user_id,)))
