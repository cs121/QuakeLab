from __future__ import annotations

import os
import shutil
from dataclasses import dataclass
from pathlib import Path

from core.services.settings_service import SettingsService


@dataclass(slots=True)
class ToolStatus:
    key: str
    label: str
    path: str
    exists: bool
    executable: bool

    @property
    def ok(self) -> bool:
        return self.exists and self.executable


_TOOL_KEYS = [
    ("qc_executable", "QC Compiler"),
    ("qbsp_executable", "QBSP"),
    ("vis_executable", "VIS"),
    ("light_executable", "LIGHT"),
    ("engine_exe", "Engine"),
]


class ToolchainCheckService:
    def __init__(self, settings: SettingsService) -> None:
        self.settings = settings

    def check_tool(self, key: str, label: str) -> ToolStatus:
        raw = self.settings.get(key, "")
        if not raw:
            return ToolStatus(key=key, label=label, path="", exists=False, executable=False)

        path = Path(raw)
        # Try shutil.which for PATH-based names
        resolved = shutil.which(raw) if not path.is_absolute() else None
        if resolved:
            path = Path(resolved)

        exists = path.exists()
        executable = exists and os.access(path, os.X_OK)
        return ToolStatus(key=key, label=label, path=str(path), exists=exists, executable=executable)

    def check_all(self) -> list[ToolStatus]:
        return [self.check_tool(key, label) for key, label in _TOOL_KEYS]

    def auto_detect_tools(self) -> dict[str, str]:
        """Try to find common Quake tool executables via PATH and known directories.

        Returns a dict mapping setting keys to found executable paths.
        """
        _CANDIDATES: dict[str, list[str]] = {
            "qc_executable": ["fteqcc", "fteqcc64", "gmqcc"],
            "qbsp_executable": ["qbsp", "tyrqbsp", "ericw-qbsp"],
            "vis_executable": ["vis", "tyrvis", "ericw-vis"],
            "light_executable": ["light", "tyrlight", "ericw-light"],
            "engine_exe": [
                "quakespasm", "quakespasm-sdl2", "vkquake",
                "ironwail", "quake", "darkplaces",
            ],
        }

        extra_dirs = [
            Path.home() / "quake" / "tools",
            Path.home() / "tools",
            Path.home() / ".local" / "bin",
            Path("/usr/local/bin"),
            Path("/usr/bin"),
        ]

        found: dict[str, str] = {}
        for key, names in _CANDIDATES.items():
            for name in names:
                resolved = shutil.which(name)
                if resolved:
                    found[key] = resolved
                    break
                for d in extra_dirs:
                    candidate = d / name
                    if candidate.exists() and os.access(candidate, os.X_OK):
                        found[key] = str(candidate)
                        break
                if key in found:
                    break
        return found
