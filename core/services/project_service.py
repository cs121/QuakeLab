from __future__ import annotations

from pathlib import Path

from infrastructure.db.database import Database


class ProjectService:
    def __init__(self, db: Database, project_root: Path) -> None:
        self.db = db
        self.project_root = project_root

    def project_name(self) -> str:
        rows = self.db.query("SELECT name FROM projects WHERE id=1")
        return rows[0]["name"] if rows else "QuakeLab"

    def absolute_path(self, relative: str) -> Path:
        return (self.project_root / relative).resolve()
