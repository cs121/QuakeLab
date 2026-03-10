from __future__ import annotations

from core.models.domain import BuildAction
from infrastructure.db.database import Database


class BuildQueueService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def enqueue(self, action: BuildAction) -> None:
        existing = self.db.query(
            "SELECT id FROM build_queue WHERE status='pending' AND action_type=? AND relative_path=?",
            (action.action_type, action.relative_path),
        )
        if existing:
            return
        self.db.execute(
            "INSERT INTO build_queue(action_type, relative_path, payload) VALUES(?, ?, ?)",
            (action.action_type, action.relative_path, action.payload),
        )

    def pop_pending(self) -> BuildAction | None:
        rows = self.db.query("SELECT id, action_type, relative_path, payload FROM build_queue WHERE status='pending' ORDER BY id LIMIT 1")
        if not rows:
            return None
        row = rows[0]
        self.db.execute("UPDATE build_queue SET status='running' WHERE id=?", (row["id"],))
        return BuildAction(row["action_type"], row["relative_path"], row["payload"])

    def mark_done(self, action: BuildAction) -> None:
        self.db.execute(
            "UPDATE build_queue SET status='done' WHERE status='running' AND action_type=? AND relative_path=?",
            (action.action_type, action.relative_path),
        )

    def mark_failed(self, action: BuildAction, message: str) -> None:
        self.db.execute(
            "UPDATE build_queue SET status='failed', payload=? WHERE status='running' AND action_type=? AND relative_path=?",
            (message, action.action_type, action.relative_path),
        )

    def latest(self, limit: int = 300) -> list[tuple]:
        rows = self.db.query(
            "SELECT enqueued_at, action_type, relative_path, status FROM build_queue ORDER BY id DESC LIMIT ?",
            (limit,),
        )
        return [(r["enqueued_at"], r["action_type"], r["relative_path"], r["status"]) for r in rows]
