from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from core.services.log_service import LogService
from core.services.settings_service import SettingsService
from infrastructure.process.runner import ProcessRunner
from infrastructure.process.streaming_runner import StreamingProcessRunner, StreamingResult


class CompilerService:
    def __init__(self, settings: SettingsService, runner: ProcessRunner, logs: LogService) -> None:
        self.settings = settings
        self.runner = runner
        self.streaming_runner = StreamingProcessRunner()
        self.logs = logs

    # --- blocking (non-streaming) -----------------------------------------

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

    # --- streaming (line-by-line output via callback) ----------------------

    def _run_tool_streaming(
        self,
        prefix: str,
        tool_key: str,
        args_key: str,
        cwd_key: str,
        extra_args: list[str],
        on_line: Callable[[str, str], None] | None = None,
    ) -> StreamingResult | None:
        exe = self.settings.get(tool_key)
        if not exe:
            self.logs.write("WARNING", prefix, f"No executable configured for {tool_key}")
            return None
        args = self.settings.get(args_key, "").split() + extra_args
        cwd = Path(self.settings.get(cwd_key, "."))
        result = self.streaming_runner.run(exe, args, cwd, on_line=on_line)
        if result.stdout:
            self.logs.write("INFO", prefix, result.stdout.strip())
        if result.stderr:
            self.logs.write("ERROR", prefix, result.stderr.strip())
        ok = result.code == 0
        self.logs.write("INFO" if ok else "ERROR", prefix, f"Exit code: {result.code}")
        return result

    def compile_qc_streaming(
        self, source_root: Path, on_line: Callable[[str, str], None] | None = None
    ) -> StreamingResult | None:
        return self._run_tool_streaming("QC", "qc_executable", "qc_args", "qc_cwd", [str(source_root)], on_line)

    def compile_map_streaming(
        self, map_file: Path, on_line: Callable[[str, str], None] | None = None
    ) -> StreamingResult | None:
        mode = self.settings.get("map_build_mode", "fast")
        result = self._run_tool_streaming(
            "QBSP", "qbsp_executable", "qbsp_args", "qbsp_cwd", [str(map_file)], on_line
        )
        if result is None or result.code != 0:
            return result
        if mode in {"full", "fast"}:
            result = self._run_tool_streaming(
                "VIS", "vis_executable", "vis_args", "vis_cwd", [str(map_file)], on_line
            )
            if result is None or result.code != 0:
                return result
        if mode == "full":
            result = self._run_tool_streaming(
                "LIGHT", "light_executable", "light_args", "light_cwd", [str(map_file)], on_line
            )
        # Check for leak pointfile after QBSP
        bsp_path = map_file.with_suffix(".bsp")
        pts_path = map_file.with_suffix(".pts")
        if pts_path.exists() and on_line:
            on_line("stderr", f"Leak detected! Pointfile: {pts_path}")
        return result

    # --- batch compilation ---------------------------------------------------

    def compile_all_maps(self) -> list[tuple[str, bool]]:
        """Compile all .map files found in source_root. Returns list of (name, ok)."""
        source_root = self.settings.source_root()
        results: list[tuple[str, bool]] = []
        for map_file in sorted(source_root.rglob("*.map")):
            ok = self.compile_map(map_file)
            results.append((map_file.name, ok))
        return results

    def compile_all_maps_streaming(
        self, on_line: Callable[[str, str], None] | None = None
    ) -> list[tuple[str, bool]]:
        """Compile all .map files with streaming output. Returns list of (name, ok)."""
        source_root = self.settings.source_root()
        results: list[tuple[str, bool]] = []
        for map_file in sorted(source_root.rglob("*.map")):
            if on_line:
                on_line("stdout", f"--- Compiling: {map_file.name} ---")
            result = self.compile_map_streaming(map_file, on_line)
            ok = result is not None and result.code == 0
            results.append((map_file.name, ok))
        return results
