from __future__ import annotations

from infrastructure.db.database import Database


class LogService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def write(self, level: str, source: str, message: str) -> None:
        self.db.execute(
            "INSERT INTO logs(level, source, message) VALUES(?, ?, ?)",
            (level, source, message),
        )

    def latest(self, limit: int = 300) -> list[tuple[str, str, str, str]]:
        rows = self.db.query(
            "SELECT ts, level, source, message FROM logs ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [(r["ts"], r["level"], r["source"], r["message"]) for r in rows]
