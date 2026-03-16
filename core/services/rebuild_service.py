from __future__ import annotations

import shutil
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from core.services.compiler_service import CompilerService
from core.services.deploy_service import DeployService
from core.services.log_service import LogService
from core.services.pack_service import PackService
from core.services.settings_service import SettingsService


@dataclass(slots=True)
class RebuildResult:
    steps: list[tuple[str, bool]] = field(default_factory=list)

    @property
    def ok(self) -> bool:
        return all(success for _, success in self.steps)

    def summary(self) -> str:
        lines = []
        for name, success in self.steps:
            status = "OK" if success else "FAILED"
            lines.append(f"  [{status}] {name}")
        return "\n".join(lines)


class RebuildService:
    def __init__(
        self,
        settings: SettingsService,
        compiler: CompilerService,
        pack: PackService,
        deploy: DeployService,
        logs: LogService,
    ) -> None:
        self.settings = settings
        self.compiler = compiler
        self.pack = pack
        self.deploy = deploy
        self.logs = logs

    def clean_build_dir(self) -> bool:
        """Remove all files in build root (except .quakelab)."""
        build_root = self.settings.build_root().resolve()
        if not build_root.exists():
            return True
        try:
            for item in build_root.iterdir():
                if item.name == ".quakelab":
                    continue
                if item.is_dir():
                    shutil.rmtree(item)
                else:
                    item.unlink()
            self.logs.write("INFO", "Rebuild", f"Cleaned build directory: {build_root}")
            return True
        except OSError as exc:
            self.logs.write("ERROR", "Rebuild", f"Clean failed: {exc}")
            return False

    def rebuild_all(
        self, on_line: Callable[[str, str], None] | None = None
    ) -> RebuildResult:
        """Full project rebuild: clean, compile QC, compile maps, pack, deploy."""
        result = RebuildResult()
        source_root = self.settings.source_root().resolve()

        # Step 1: Clean
        ok = self.clean_build_dir()
        result.steps.append(("Clean build directory", ok))
        if not ok:
            return result

        # Step 2: Compile QC
        self.logs.write("INFO", "Rebuild", "Compiling QuakeC...")
        qc_result = self.compiler.compile_qc_streaming(source_root, on_line=on_line)
        qc_ok = qc_result is not None and qc_result.code == 0
        result.steps.append(("Compile QC", qc_ok))

        # Step 3: Compile all maps
        map_files = sorted(source_root.rglob("*.map"))
        if map_files:
            all_maps_ok = True
            for map_file in map_files:
                self.logs.write("INFO", "Rebuild", f"Compiling map: {map_file.name}")
                map_result = self.compiler.compile_map_streaming(map_file, on_line=on_line)
                if map_result is None or map_result.code != 0:
                    all_maps_ok = False
            result.steps.append((f"Compile {len(map_files)} map(s)", all_maps_ok))
        else:
            result.steps.append(("Compile maps (none found)", True))

        # Step 4: Build PAK
        self.logs.write("INFO", "Rebuild", "Rebuilding PAK archive...")
        pak_ok = self.pack.rebuild_pak()
        result.steps.append(("Build PAK", pak_ok))

        # Step 5: Deploy
        if self.settings.get("deploy_after_build", "0") == "1":
            self.logs.write("INFO", "Rebuild", "Deploying...")
            deploy_ok = self.deploy.deploy_pak()
            result.steps.append(("Deploy", deploy_ok))

        self.logs.write("INFO", "Rebuild", f"Rebuild complete.\n{result.summary()}")
        return result
