from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

# Quake 1 BSP version
BSP_VERSION_Q1 = 29

# Lump indices and names for Quake 1 BSP
_LUMP_NAMES = [
    "entities",     # 0
    "planes",       # 1
    "textures",     # 2
    "vertices",     # 3
    "visibility",   # 4
    "nodes",        # 5
    "texinfo",      # 6
    "faces",        # 7
    "lighting",     # 8
    "clipnodes",    # 9
    "leaves",       # 10
    "marksurfaces", # 11
    "edges",        # 12
    "surfedges",    # 13
    "models",       # 14
]

_HEADER_STRUCT = struct.Struct("<i")  # version
_LUMP_STRUCT = struct.Struct("<ii")   # offset, length


class BspFormatError(Exception):
    """Raised when a BSP file is malformed."""


@dataclass(slots=True)
class BspInfo:
    version: int
    lump_sizes: dict[str, int] = field(default_factory=dict)
    entity_count: int = 0
    texture_names: list[str] = field(default_factory=list)
    face_count: int = 0
    model_count: int = 0
    raw_entities: str = ""


def read_bsp_info(path: Path) -> BspInfo:
    """Read basic information from a Quake 1 BSP file."""
    data = path.read_bytes()

    if len(data) < 4 + 15 * 8:
        raise BspFormatError("File too small to be a valid BSP")

    version = _HEADER_STRUCT.unpack_from(data, 0)[0]
    if version != BSP_VERSION_Q1:
        raise BspFormatError(f"Unsupported BSP version: {version} (expected {BSP_VERSION_Q1})")

    info = BspInfo(version=version)

    # Parse lump directory (15 lumps, each 8 bytes: offset + length)
    lumps: list[tuple[int, int]] = []
    for i in range(15):
        offset, length = _LUMP_STRUCT.unpack_from(data, 4 + i * 8)
        name = _LUMP_NAMES[i] if i < len(_LUMP_NAMES) else f"lump_{i}"
        info.lump_sizes[name] = length
        lumps.append((offset, length))

    # Parse entities lump (lump 0) - raw ASCII text
    ent_offset, ent_length = lumps[0]
    if ent_length > 0 and ent_offset + ent_length <= len(data):
        raw = data[ent_offset:ent_offset + ent_length]
        info.raw_entities = raw.decode("ascii", errors="replace").rstrip("\x00")
        info.entity_count = info.raw_entities.count('"classname"')

    # Parse texture lump (lump 2) - MIP texture directory
    tex_offset, tex_length = lumps[2]
    if tex_length >= 4 and tex_offset + 4 <= len(data):
        num_textures = struct.unpack_from("<i", data, tex_offset)[0]
        # Each texture entry offset is 4 bytes after the count
        for i in range(num_textures):
            entry_ptr_offset = tex_offset + 4 + i * 4
            if entry_ptr_offset + 4 > len(data):
                break
            tex_entry_offset = struct.unpack_from("<i", data, entry_ptr_offset)[0]
            if tex_entry_offset < 0:
                continue  # -1 means missing texture
            abs_offset = tex_offset + tex_entry_offset
            if abs_offset + 16 > len(data):
                break
            # MIP texture name is 16 bytes at the start
            name_bytes = data[abs_offset:abs_offset + 16]
            name = name_bytes.split(b"\x00", 1)[0].decode("ascii", errors="replace")
            if name:
                info.texture_names.append(name)

    # Face count from faces lump (lump 7), each face is 20 bytes in Q1
    face_offset, face_length = lumps[7]
    if face_length > 0:
        info.face_count = face_length // 20

    # Model count from models lump (lump 14), each model is 64 bytes in Q1
    model_offset, model_length = lumps[14]
    if model_length > 0:
        info.model_count = model_length // 64

    return info
