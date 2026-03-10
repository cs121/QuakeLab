from __future__ import annotations

import sqlite3
from pathlib import Path


SCHEMA = """
CREATE TABLE IF NOT EXISTS projects (
    id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    root_path TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS toolchains (
    id INTEGER PRIMARY KEY,
    tool_type TEXT NOT NULL,
    name TEXT NOT NULL,
    executable TEXT NOT NULL,
    working_directory TEXT NOT NULL,
    default_args TEXT DEFAULT ''
);

CREATE TABLE IF NOT EXISTS change_journal (
    id INTEGER PRIMARY KEY,
    ts TEXT NOT NULL,
    project TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    absolute_path TEXT,
    change_type TEXT NOT NULL,
    old_hash TEXT,
    new_hash TEXT,
    size INTEGER,
    mtime REAL,
    normalized INTEGER DEFAULT 1,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS build_queue (
    id INTEGER PRIMARY KEY,
    enqueued_at TEXT DEFAULT CURRENT_TIMESTAMP,
    action_type TEXT NOT NULL,
    relative_path TEXT NOT NULL,
    payload TEXT,
    status TEXT DEFAULT 'pending'
);

CREATE TABLE IF NOT EXISTS logs (
    id INTEGER PRIMARY KEY,
    ts TEXT DEFAULT CURRENT_TIMESTAMP,
    level TEXT NOT NULL,
    source TEXT NOT NULL,
    message TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS file_state (
    relative_path TEXT PRIMARY KEY,
    file_hash TEXT,
    size INTEGER,
    mtime REAL,
    last_seen TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


DEFAULT_SETTINGS = {
    "project_name": "QuakeForge",
    "source_root": "src",
    "build_root": "build",
    "deploy_root": "deploy",
    "pak_output_path": "build/pak0.pak",
    "auto_watch": "1",
    "auto_flush": "1",
    "flush_interval_minutes": "3",
    "pack_after_build": "1",
    "deploy_after_build": "0",
    "map_build_mode": "fast",
    "engine_exe": "",
    "engine_args": "",
}


class Database:
    def __init__(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        self.path = path
        self.conn = sqlite3.connect(path)
        self.conn.row_factory = sqlite3.Row
        self._init()

    def _init(self) -> None:
        self.conn.executescript(SCHEMA)
        for key, value in DEFAULT_SETTINGS.items():
            self.conn.execute(
                "INSERT OR IGNORE INTO settings(key, value) VALUES(?, ?)",
                (key, value),
            )
        self.conn.execute(
            "INSERT OR IGNORE INTO projects(id, name, root_path) VALUES(1, ?, ?)",
            ("QuakeForge", str(self.path.parent.parent)),
        )
        self.conn.commit()

    def execute(self, sql: str, params: tuple = ()):
        cur = self.conn.execute(sql, params)
        self.conn.commit()
        return cur

    def query(self, sql: str, params: tuple = ()) -> list[sqlite3.Row]:
        return list(self.conn.execute(sql, params))
