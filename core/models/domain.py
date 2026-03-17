from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass(slots=True)
class FileChange:
    timestamp: datetime
    project: str
    relative_path: str
    absolute_path: str
    change_type: str
    old_hash: str | None = None
    new_hash: str | None = None
    size: int | None = None
    mtime: float | None = None
    normalized: bool = True
    notes: str | None = None


@dataclass(slots=True)
class BuildAction:
    action_type: str
    relative_path: str
    payload: str | None = None


@dataclass(slots=True)
class ToolchainConfig:
    name: str
    executable: str
    working_directory: str
    default_args: str = ""


@dataclass(slots=True)
class ProjectPaths:
    source_root: Path
    build_root: Path
    deploy_root: Path
    pak_output_path: Path


@dataclass(slots=True)
class CompilerDiagnostic:
    file_path: str
    line: int
    column: int | None
    severity: str  # "error", "warning"
    message: str


@dataclass(slots=True)
class ValidationDiagnostic:
    file_path: str
    line: int
    severity: str  # "error", "warning", "info"
    message: str


@dataclass(slots=True)
class BuildTemplate:
    name: str
    qbsp_args: str = ""
    vis_args: str = ""
    light_args: str = ""
    skip_vis: bool = False
    skip_light: bool = False
    description: str = ""


BUILTIN_TEMPLATES: list[BuildTemplate] = [
    BuildTemplate(
        name="preview",
        qbsp_args="",
        skip_vis=True,
        skip_light=True,
        description="QBSP only – instant preview, no VIS or LIGHT",
    ),
    BuildTemplate(
        name="fast",
        qbsp_args="",
        vis_args="-fast",
        skip_light=True,
        description="QBSP + fast VIS, no LIGHT – good for iteration",
    ),
    BuildTemplate(
        name="normal",
        qbsp_args="",
        vis_args="",
        light_args="",
        skip_vis=False,
        skip_light=False,
        description="QBSP + full VIS + LIGHT – standard quality",
    ),
    BuildTemplate(
        name="high",
        qbsp_args="",
        vis_args="-level 4",
        light_args="-extra4 -soft",
        skip_vis=False,
        skip_light=False,
        description="QBSP + full VIS level4 + LIGHT extra4 – high quality",
    ),
    BuildTemplate(
        name="custom",
        qbsp_args="",
        vis_args="",
        light_args="",
        skip_vis=False,
        skip_light=False,
        description="Custom args – configure in Build Templates settings",
    ),
]
