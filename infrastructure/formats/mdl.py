"""Quake 1 MDL (IDPO version 6) model format parser."""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

MAGIC = b"IDPO"
VERSION = 6


@dataclass
class MdlInfo:
    scale: tuple[float, float, float]
    translate: tuple[float, float, float]
    bounding_radius: float
    num_skins: int
    skin_width: int
    skin_height: int
    num_verts: int
    num_tris: int
    num_frames: int
    flags: int
    # First skin pixels (palette indices), empty if group skin or error
    first_skin_pixels: bytes = b""


class MdlError(Exception):
    pass


def read_mdl_info(path: Path) -> MdlInfo:
    data = path.read_bytes()
    if len(data) < 84:
        raise MdlError("File too small to be an MDL")

    magic = data[:4]
    version = struct.unpack_from("<i", data, 4)[0]
    if magic != MAGIC:
        raise MdlError(f"Not an IDPO MDL file (magic={magic!r})")
    if version != VERSION:
        raise MdlError(f"Unsupported MDL version {version} (expected {VERSION})")

    scale = struct.unpack_from("<fff", data, 8)
    translate = struct.unpack_from("<fff", data, 20)
    bounding_radius = struct.unpack_from("<f", data, 32)[0]
    # eye_pos at 36 (12 bytes) – skip
    num_skins, skin_w, skin_h = struct.unpack_from("<iii", data, 48)
    num_verts, num_tris, num_frames = struct.unpack_from("<iii", data, 60)
    # sync_type at 72, flags at 76, size at 80
    flags = struct.unpack_from("<i", data, 76)[0]

    # Read first skin (offset 84)
    skin_pixels = b""
    skin_size = skin_w * skin_h
    pos = 84
    if num_skins > 0 and skin_size > 0:
        if pos + 4 > len(data):
            raise MdlError("MDL skin data truncated")
        skin_type = struct.unpack_from("<i", data, pos)[0]
        pos += 4
        if skin_type == 0:
            # Single skin
            if pos + skin_size <= len(data):
                skin_pixels = data[pos: pos + skin_size]

    return MdlInfo(
        scale=scale,
        translate=translate,
        bounding_radius=bounding_radius,
        num_skins=num_skins,
        skin_width=skin_w,
        skin_height=skin_h,
        num_verts=num_verts,
        num_tris=num_tris,
        num_frames=num_frames,
        flags=flags,
        first_skin_pixels=skin_pixels,
    )
