from __future__ import annotations

from collections.abc import Callable
from pathlib import Path

from core.models.domain import BUILTIN_TEMPLATES, BuildTemplate
from core.services.log_service import LogService
from core.services.settings_service import SettingsService
from infrastructure.process.runner import ProcessRunner
from infrastructure.process.streaming_runner import StreamingProcessRunner, StreamingResult


def _resolve_template(settings: SettingsService) -> BuildTemplate:
    """Return the active BuildTemplate, merging custom settings if needed."""
    name = settings.get("build_template", "fast")
    for tpl in BUILTIN_TEMPLATES:
        if tpl.name == name:
            if name == "custom":
                # Use per-field overrides stored in settings
                return BuildTemplate(
                    name="custom",
                    qbsp_args=settings.get("template_qbsp_args", ""),
                    vis_args=settings.get("template_vis_args", ""),
                    light_args=settings.get("template_light_args", ""),
                    skip_vis=settings.get("template_skip_vis", "0") == "1",
                    skip_light=settings.get("template_skip_light", "0") == "1",
                )
            return tpl
    # Fallback to legacy map_build_mode setting
    mode = settings.get("map_build_mode", "fast")
    if mode == "full":
        return BuildTemplate(name="normal")
    if mode == "manual":
        return BuildTemplate(name="preview", skip_vis=True, skip_light=True)
    return BuildTemplate(name="fast", vis_args="-fast", skip_light=True)


class CompilerService:
    def __init__(self, settings: SettingsService, runner: ProcessRunner, logs: LogService) -> None:
        self.settings = settings
        self.runner = runner
        self.streaming_runner = StreamingProcessRunner()
        self.logs = logs

    # --- blocking (non-streaming) -----------------------------------------

    def _run_tool(self, prefix: str, tool_key: str, extra_args: list[str]) -> bool:
        exe = self.settings.get(tool_key)
        if not exe:
            self.logs.write("WARNING", prefix, f"No executable configured for {tool_key}")
            return False
        result = self.runner.run(exe, extra_args, Path("."))
        if result.stdout:
            self.logs.write("INFO", prefix, result.stdout.strip())
        if result.stderr:
            self.logs.write("ERROR", prefix, result.stderr.strip())
        ok = result.code == 0
        self.logs.write("INFO" if ok else "ERROR", prefix, f"Exit code: {result.code}")
        return ok

    def compile_qc(self, source_root: Path) -> bool:
        exe = self.settings.get("qc_executable")
        if not exe:
            self.logs.write("WARNING", "QC", "No QC executable configured")
            return False
        args = self.settings.get("qc_args", "").split() + [str(source_root)]
        result = self.runner.run(exe, args, Path(self.settings.get("qc_cwd", ".")))
        if result.stdout:
            self.logs.write("INFO", "QC", result.stdout.strip())
        if result.stderr:
            self.logs.write("ERROR", "QC", result.stderr.strip())
        ok = result.code == 0
        self.logs.write("INFO" if ok else "ERROR", "QC", f"Exit code: {result.code}")
        return ok

    def compile_map(self, map_file: Path) -> bool:
        template = _resolve_template(self.settings)
        qbsp_args = template.qbsp_args.split() + [str(map_file)]
        ok = self._run_tool_with_args("QBSP", "qbsp_executable", qbsp_args)
        if ok and not template.skip_vis:
            vis_args = template.vis_args.split() + [str(map_file)]
            ok = self._run_tool_with_args("VIS", "vis_executable", vis_args)
        if ok and not template.skip_light:
            light_args = template.light_args.split() + [str(map_file)]
            ok = self._run_tool_with_args("LIGHT", "light_executable", light_args)
        return ok

    def _run_tool_with_args(self, prefix: str, tool_key: str, args: list[str]) -> bool:
        exe = self.settings.get(tool_key)
        if not exe:
            self.logs.write("WARNING", prefix, f"No executable configured for {tool_key}")
            return False
        result = self.runner.run(exe, args, Path("."))
        if result.stdout:
            self.logs.write("INFO", prefix, result.stdout.strip())
        if result.stderr:
            self.logs.write("ERROR", prefix, result.stderr.strip())
        ok = result.code == 0
        self.logs.write("INFO" if ok else "ERROR", prefix, f"Exit code: {result.code}")
        return ok

    # --- streaming (line-by-line output via callback) ----------------------

    def _run_tool_streaming(
        self,
        prefix: str,
        tool_key: str,
        args: list[str],
        on_line: Callable[[str, str], None] | None = None,
    ) -> StreamingResult | None:
        exe = self.settings.get(tool_key)
        if not exe:
            self.logs.write("WARNING", prefix, f"No executable configured for {tool_key}")
            return None
        result = self.streaming_runner.run(exe, args, Path("."), on_line=on_line)
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
        exe = self.settings.get("qc_executable")
        if not exe:
            self.logs.write("WARNING", "QC", "No QC executable configured")
            return None
        args = self.settings.get("qc_args", "").split() + [str(source_root)]
        return self._run_tool_streaming("QC", "qc_executable", args, on_line)

    def compile_map_streaming(
        self,
        map_file: Path,
        on_line: Callable[[str, str], None] | None = None,
        template_name: str | None = None,
    ) -> StreamingResult | None:
        if template_name is not None:
            # Override active template for this call
            for tpl in BUILTIN_TEMPLATES:
                if tpl.name == template_name:
                    template = tpl
                    break
            else:
                template = _resolve_template(self.settings)
        else:
            template = _resolve_template(self.settings)

        qbsp_args = template.qbsp_args.split() + [str(map_file)]
        result = self._run_tool_streaming("QBSP", "qbsp_executable", qbsp_args, on_line)
        if result is None or result.code != 0:
            return result
        if not template.skip_vis:
            vis_args = template.vis_args.split() + [str(map_file)]
            result = self._run_tool_streaming("VIS", "vis_executable", vis_args, on_line)
            if result is None or result.code != 0:
                return result
        if not template.skip_light:
            light_args = template.light_args.split() + [str(map_file)]
            result = self._run_tool_streaming("LIGHT", "light_executable", light_args, on_line)
        return result
