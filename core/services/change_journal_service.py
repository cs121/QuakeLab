from __future__ import annotations

from core.models.domain import FileChange
from infrastructure.db.database import Database


class ChangeJournalService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def add(self, change: FileChange) -> None:
        self.db.execute(
            """
            INSERT INTO change_journal(ts, project, relative_path, absolute_path, change_type, old_hash, new_hash, size, mtime, normalized, notes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                change.timestamp.isoformat(),
                change.project,
                change.relative_path,
                change.absolute_path,
                change.change_type,
                change.old_hash,
                change.new_hash,
                change.size,
                change.mtime,
                int(change.normalized),
                change.notes,
            ),
        )

    def latest(self, limit: int = 300) -> list[tuple]:
        rows = self.db.query(
            "SELECT ts, change_type, relative_path, new_hash, notes FROM change_journal ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [(r["ts"], r["change_type"], r["relative_path"], r["new_hash"], r["notes"] or "") for r in rows]
