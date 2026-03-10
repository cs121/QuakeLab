from __future__ import annotations

import json
from pathlib import Path

from infrastructure.db.database import Database


class SettingsService:
    def __init__(self, db: Database) -> None:
        self.db = db

    def get(self, key: str, default: str = "") -> str:
        rows = self.db.query("SELECT value FROM settings WHERE key=?", (key,))
        return rows[0]["value"] if rows else default

    def set(self, key: str, value: str) -> None:
        self.db.execute(
            "INSERT INTO settings(key, value) VALUES(?, ?) ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (key, value),
        )

    def all(self) -> dict[str, str]:
        rows = self.db.query("SELECT key, value FROM settings ORDER BY key")
        return {row["key"]: row["value"] for row in rows}

    def export_json(self, path: Path) -> None:
        path.write_text(json.dumps(self.all(), indent=2), encoding="utf-8")

    def import_json(self, path: Path) -> None:
        payload = json.loads(path.read_text(encoding="utf-8"))
        for key, value in payload.items():
            self.set(key, str(value))

    def source_root(self) -> Path:
        return Path(self.get("source_root", "src"))

    def build_root(self) -> Path:
        return Path(self.get("build_root", "build"))

    def deploy_root(self) -> Path:
        return Path(self.get("deploy_root", "deploy"))

    def pak_output_path(self) -> Path:
        return Path(self.get("pak_output_path", "build/pak0.pak"))
