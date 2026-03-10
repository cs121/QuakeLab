from __future__ import annotations

from pathlib import Path

from core.models.domain import BuildAction

QC_EXTENSIONS = {".qc"}
TEXT_EXTENSIONS = {".txt", ".cfg", ".shader", ".src", ".map"}
GLSL_EXTENSIONS = {".glsl", ".vert", ".frag"}
IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".tga", ".bmp"}
AUDIO_EXTENSIONS = {".wav", ".mp3"}


def resolve_actions(relative_path: str, change_type: str) -> list[BuildAction]:
    path = Path(relative_path)
    ext = path.suffix.lower()
    actions: list[BuildAction] = []

    if path.name.lower() == "progs.src" or ext in QC_EXTENSIONS:
        actions.append(BuildAction("compile_qc", relative_path))
    elif ext == ".map":
        actions.append(BuildAction("compile_map", relative_path))

    if change_type == "deleted":
        actions.append(BuildAction("remove_asset", relative_path))
    elif ext in IMAGE_EXTENSIONS | AUDIO_EXTENSIONS | GLSL_EXTENSIONS | TEXT_EXTENSIONS:
        actions.append(BuildAction("pack_asset", relative_path))

    if actions:
        actions.append(BuildAction("rebuild_pak", "*"))

    return actions
