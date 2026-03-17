"""Quake 1 SPR (IDSP version 1) sprite format parser."""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

MAGIC = b"IDSP"
VERSION = 1

SPR_TYPE_LABELS = {
    0: "VP_PARALLEL_UPRIGHT",
    1: "VP_FACING_UPRIGHT",
    2: "VP_PARALLEL",
    3: "FIXED",
    4: "VP_PARALLEL_ORIENTED",
}


@dataclass
class SprFrame:
    width: int
    height: int
    origin_x: int
    origin_y: int
    pixels: bytes       # width × height palette indices


@dataclass
class SprInfo:
    spr_type: int
    bounding_radius: float
    max_width: int
    max_height: int
    num_frames: int
    frames: list[SprFrame] = field(default_factory=list)

    @property
    def type_label(self) -> str:
        return SPR_TYPE_LABELS.get(self.spr_type, str(self.spr_type))


class SprError(Exception):
    pass


def read_spr_info(path: Path) -> SprInfo:
    data = path.read_bytes()
    if len(data) < 36:
        raise SprError("File too small to be an SPR")

    magic = data[:4]
    version = struct.unpack_from("<i", data, 4)[0]
    if magic != MAGIC:
        raise SprError(f"Not an IDSP sprite file (magic={magic!r})")
    if version != VERSION:
        raise SprError(f"Unsupported SPR version {version} (expected {VERSION})")

    spr_type = struct.unpack_from("<i", data, 8)[0]
    bounding_radius = struct.unpack_from("<f", data, 12)[0]
    max_width, max_height = struct.unpack_from("<ii", data, 16)
    num_frames = struct.unpack_from("<i", data, 24)[0]
    # beam_length at 28, sync_type at 32

    info = SprInfo(
        spr_type=spr_type,
        bounding_radius=bounding_radius,
        max_width=max_width,
        max_height=max_height,
        num_frames=num_frames,
    )

    pos = 36
    for _ in range(min(num_frames, 64)):  # cap to avoid huge allocations
        if pos + 4 > len(data):
            break
        group = struct.unpack_from("<i", data, pos)[0]
        pos += 4

        if group == 0:
            # Single frame
            if pos + 16 > len(data):
                break
            origin_x, origin_y, width, height = struct.unpack_from("<iiii", data, pos)
            pos += 16
            pixel_count = width * height
            if pixel_count <= 0 or pixel_count > 2_000_000:
                break
            if pos + pixel_count > len(data):
                break
            pixels = data[pos: pos + pixel_count]
            pos += pixel_count
            info.frames.append(SprFrame(width=width, height=height, origin_x=origin_x, origin_y=origin_y, pixels=pixels))
        else:
            # Group frame – skip (count + floats + individual frames)
            if pos + 4 > len(data):
                break
            count = struct.unpack_from("<i", data, pos)[0]
            pos += 4 + count * 4  # skip intervals
            for _ in range(count):
                if pos + 16 > len(data):
                    break
                _ox, _oy, w, h = struct.unpack_from("<iiii", data, pos)
                pos += 16 + w * h
            break  # stop after first group to avoid complexity

    return info
