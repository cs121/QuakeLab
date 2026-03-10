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
