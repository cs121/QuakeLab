from __future__ import annotations

import subprocess
from pathlib import Path

from core.services.log_service import LogService
from core.services.settings_service import SettingsService
from infrastructure.process.streaming_runner import run_detached


class LaunchService:
    def __init__(self, settings: SettingsService, logs: LogService) -> None:
        self.settings = settings
        self.logs = logs

    def launch_game(self) -> subprocess.Popen | None:
        """Launch the configured game engine pointing at the mod directory."""
        exe = self.settings.get("engine_exe", "")
        if not exe:
            self.logs.write("WARNING", "Launch", "No engine executable configured")
            return None

        exe_path = Path(exe)
        if not exe_path.exists():
            self.logs.write("ERROR", "Launch", f"Engine executable not found: {exe}")
            return None

        deploy_root = self.settings.deploy_root().resolve()
        engine_args_str = self.settings.get("engine_args", "")
        args: list[str] = engine_args_str.split() if engine_args_str else []

        # Add -game <mod_dir> if deploy root has a parent (engine base directory)
        if deploy_root.exists():
            args.extend(["-game", deploy_root.name])
            cwd = deploy_root.parent
        else:
            cwd = None

        self.logs.write("INFO", "Launch", f"Starting {exe_path.name} {' '.join(args)}")
        try:
            proc = run_detached(str(exe_path), args, cwd=cwd)
            self.logs.write("INFO", "Launch", f"Engine started (PID {proc.pid})")
            return proc
        except OSError as exc:
            self.logs.write("ERROR", "Launch", f"Failed to start engine: {exc}")
            return None
