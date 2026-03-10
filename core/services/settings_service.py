from __future__ import annotations

import json
import shutil
from pathlib import Path

from infrastructure.db.database import Database


class SettingsService:
    def __init__(self, db: Database, project_root: Path) -> None:
        self.db = db
        self.project_root = project_root.resolve()

    def _project_base_root(self) -> Path:
        source_setting = Path(self.get("source_root", "src"))
        if source_setting.is_absolute():
            return source_setting.parent
        return self.project_root

    def _resolve_path(self, raw_path: str) -> Path:
        path = Path(raw_path)
        if path.is_absolute():
            return path.resolve()
        return (self._project_base_root() / path).resolve()

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


    def _is_within_project_root(self, path: Path) -> bool:
        try:
            path.resolve().relative_to(self.project_root)
            return True
        except ValueError:
            return False

    def reset_workspace(self) -> None:
        roots_to_clean = {
            self.source_root(),
            self.build_root(),
            self.deploy_root(),
            (self.project_root / "src").resolve(),
            (self.project_root / "build").resolve(),
            (self.project_root / "deploy").resolve(),
        }

        self.db.rebuild()

        for root in roots_to_clean:
            if root.exists() and root.is_dir() and self._is_within_project_root(root):
                shutil.rmtree(root)

        self.source_root().mkdir(parents=True, exist_ok=True)
        self.build_root().mkdir(parents=True, exist_ok=True)
        self.deploy_root().mkdir(parents=True, exist_ok=True)
        self.pak_output_path().parent.mkdir(parents=True, exist_ok=True)

    def source_root(self) -> Path:
        return self._resolve_path(self.get("source_root", "src"))

    def build_root(self) -> Path:
        return self._resolve_path(self.get("build_root", "build"))

    def deploy_root(self) -> Path:
        return self._resolve_path(self.get("deploy_root", "deploy"))

    def pak_output_path(self) -> Path:
        return self._resolve_path(self.get("pak_output_path", "build/pak0.pak"))
