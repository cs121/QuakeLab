from __future__ import annotations

from pathlib import Path

from core.services.log_service import LogService
from core.services.settings_service import SettingsService
from infrastructure.process.runner import ProcessRunner


class CompilerService:
    def __init__(self, settings: SettingsService, runner: ProcessRunner, logs: LogService) -> None:
        self.settings = settings
        self.runner = runner
        self.logs = logs

    def _run_tool(self, prefix: str, tool_key: str, args_key: str, cwd_key: str, extra_args: list[str]) -> bool:
        exe = self.settings.get(tool_key)
        if not exe:
            self.logs.write("WARNING", prefix, f"No executable configured for {tool_key}")
            return False
        args = self.settings.get(args_key, "").split() + extra_args
        cwd = Path(self.settings.get(cwd_key, "."))
        result = self.runner.run(exe, args, cwd)
        if result.stdout:
            self.logs.write("INFO", prefix, result.stdout.strip())
        if result.stderr:
            self.logs.write("ERROR", prefix, result.stderr.strip())
        ok = result.code == 0
        self.logs.write("INFO" if ok else "ERROR", prefix, f"Exit code: {result.code}")
        return ok

    def compile_qc(self, source_root: Path) -> bool:
        return self._run_tool("QC", "qc_executable", "qc_args", "qc_cwd", [str(source_root)])

    def compile_map(self, map_file: Path) -> bool:
        mode = self.settings.get("map_build_mode", "fast")
        ok = self._run_tool("QBSP", "qbsp_executable", "qbsp_args", "qbsp_cwd", [str(map_file)])
        if ok and mode in {"full", "fast"}:
            ok = self._run_tool("VIS", "vis_executable", "vis_args", "vis_cwd", [str(map_file)])
        if ok and mode == "full":
            ok = self._run_tool("LIGHT", "light_executable", "light_args", "light_cwd", [str(map_file)])
        return ok
