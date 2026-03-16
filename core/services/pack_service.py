from __future__ import annotations

import fnmatch
import json
import shutil
from pathlib import Path

from core.services.log_service import LogService
from core.services.settings_service import SettingsService
from infrastructure.archives.pak import PakArchive, PakError


class PackService:
    def __init__(self, settings: SettingsService, pak: PakArchive, logs: LogService) -> None:
        self.settings = settings
        self.pak = pak
        self.logs = logs

    def _collect_files(self) -> list[tuple[str, Path]]:
        source_root = self.settings.source_root()
        build_root = self.settings.build_root()
        output_path = self.settings.pak_output_path().resolve()
        files: list[tuple[str, Path]] = []

        for root in (source_root, build_root):
            if not root.exists():
                continue
            for path in root.rglob("*"):
                if not path.is_file():
                    continue
                resolved = path.resolve()
                if resolved == output_path:
                    continue
                rel = path.relative_to(root).as_posix()
                files.append((rel, path))
        return files

    def _collect_files_matching(self, patterns: list[str]) -> list[tuple[str, Path]]:
        """Collect files matching any of the given glob patterns."""
        all_files = self._collect_files()
        if patterns == ["*"]:
            return all_files
        matched: list[tuple[str, Path]] = []
        for rel, path in all_files:
            for pattern in patterns:
                if fnmatch.fnmatch(rel, pattern):
                    matched.append((rel, path))
                    break
        return matched

    def rebuild_pak(self) -> bool:
        output = self.settings.pak_output_path()
        files = self._collect_files()
        if not files:
            self.logs.write("WARNING", "Pack", "No files collected. Writing empty PAK archive.")

        backup = output.with_suffix(output.suffix + ".bak")
        try:
            if output.exists():
                shutil.copy2(output, backup)
            self.pak.write(output, files)
            self.logs.write("INFO", "Pack", f"PAK rebuilt with {len(files)} entries: {output}")
            return True
        except PakError as exc:
            self.logs.write("ERROR", "Pack", f"PAK rebuild failed: {exc}")
            if backup.exists():
                backup.replace(output)
            return False
        except Exception as exc:  # noqa: BLE001
            self.logs.write("ERROR", "Pack", f"Unexpected PAK rebuild failure: {exc}")
            if backup.exists():
                backup.replace(output)
            return False

    def rebuild_paks(self) -> bool:
        """Build multiple PAK files based on pak_definitions setting.

        pak_definitions is a JSON string mapping PAK names to glob patterns:
        {"pak0.pak": ["progs.dat", "maps/*"], "pak1.pak": ["gfx/*", "textures/*"]}

        Falls back to single PAK via rebuild_pak() if not configured.
        """
        defs_json = self.settings.get("pak_definitions", "")
        if not defs_json:
            return self.rebuild_pak()

        try:
            definitions: dict[str, list[str]] = json.loads(defs_json)
        except json.JSONDecodeError as exc:
            self.logs.write("ERROR", "Pack", f"Invalid pak_definitions JSON: {exc}")
            return False

        build_root = self.settings.build_root()
        all_ok = True

        for pak_name, patterns in definitions.items():
            output = build_root / pak_name
            files = self._collect_files_matching(patterns)
            backup = output.with_suffix(output.suffix + ".bak")

            try:
                if output.exists():
                    shutil.copy2(output, backup)
                self.pak.write(output, files)
                self.logs.write(
                    "INFO", "Pack",
                    f"{pak_name}: {len(files)} entries ({', '.join(patterns)})"
                )
            except (PakError, Exception) as exc:
                self.logs.write("ERROR", "Pack", f"{pak_name} failed: {exc}")
                if backup.exists():
                    backup.replace(output)
                all_ok = False

        return all_ok

    def list_pak(self) -> list[str]:
        output = self.settings.pak_output_path()
        if not output.exists():
            return []
        return [entry.name for entry in self.pak.read_entries(output)]
