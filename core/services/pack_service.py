from __future__ import annotations

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

    def list_pak(self) -> list[str]:
        output = self.settings.pak_output_path()
        if not output.exists():
            return []
        return [entry.name for entry in self.pak.read_entries(output)]
