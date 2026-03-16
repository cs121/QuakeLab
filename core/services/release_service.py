from __future__ import annotations

import zipfile
from pathlib import Path

from core.services.log_service import LogService
from core.services.settings_service import SettingsService


class ReleaseService:
    def __init__(self, settings: SettingsService, logs: LogService) -> None:
        self.settings = settings
        self.logs = logs

    def create_release(self, output_path: Path) -> bool:
        """Create a release ZIP archive containing PAK files and extras.

        The ZIP contains a top-level directory named after the mod,
        with PAK files, readme, and any .cfg files.
        """
        build_root = self.settings.build_root().resolve()
        source_root = self.settings.source_root().resolve()
        project_root = source_root.parent

        # Determine mod name from deploy directory or project root
        deploy_root = self.settings.deploy_root().resolve()
        mod_name = deploy_root.name or project_root.name or "quakemod"

        # Collect files for the release
        release_files: list[tuple[str, Path]] = []

        # PAK files from build root
        for pak_file in sorted(build_root.glob("*.pak")):
            release_files.append((f"{mod_name}/{pak_file.name}", pak_file))

        # Also check the configured pak output path
        pak_output = self.settings.pak_output_path().resolve()
        if pak_output.exists() and pak_output.parent != build_root:
            release_files.append((f"{mod_name}/{pak_output.name}", pak_output))

        # readme.txt from project root or source root
        for readme_name in ("readme.txt", "README.txt", "README.md"):
            for search_root in (project_root, source_root):
                readme = search_root / readme_name
                if readme.exists():
                    release_files.append((f"{mod_name}/{readme_name}", readme))
                    break

        # .cfg files from source root
        for cfg_file in source_root.rglob("*.cfg"):
            rel = cfg_file.relative_to(source_root).as_posix()
            release_files.append((f"{mod_name}/{rel}", cfg_file))

        # Extra patterns from settings
        extra_patterns = self.settings.get("release_include_patterns", "")
        if extra_patterns:
            for pattern in extra_patterns.split(","):
                pattern = pattern.strip()
                if pattern:
                    for match in source_root.rglob(pattern):
                        if match.is_file():
                            rel = match.relative_to(source_root).as_posix()
                            release_files.append((f"{mod_name}/{rel}", match))

        if not release_files:
            self.logs.write("WARNING", "Release", "No files to include in release.")
            return False

        # Deduplicate by archive path
        seen: set[str] = set()
        unique_files: list[tuple[str, Path]] = []
        for arc_name, path in release_files:
            if arc_name not in seen:
                seen.add(arc_name)
                unique_files.append((arc_name, path))

        try:
            output_path.parent.mkdir(parents=True, exist_ok=True)
            with zipfile.ZipFile(output_path, "w", zipfile.ZIP_DEFLATED) as zf:
                for arc_name, file_path in unique_files:
                    zf.write(file_path, arc_name)

            self.logs.write(
                "INFO", "Release",
                f"Release created: {output_path} ({len(unique_files)} files)"
            )
            return True
        except OSError as exc:
            self.logs.write("ERROR", "Release", f"Failed to create release: {exc}")
            return False
