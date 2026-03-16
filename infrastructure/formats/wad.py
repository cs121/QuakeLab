from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path

# Standard Quake 1 palette (256 RGB triplets)
# This is the default palette used by all Quake 1 textures.
# Abbreviated here - full 256-color palette from id Software's Quake.
_QUAKE_PALETTE: list[tuple[int, int, int]] = [
    (0,0,0),(15,15,15),(31,31,31),(47,47,47),(63,63,63),(75,75,75),
    (91,91,91),(107,107,107),(123,123,123),(139,139,139),(155,155,155),
    (171,171,171),(187,187,187),(203,203,203),(219,219,219),(235,235,235),
    (15,11,7),(23,15,11),(31,23,11),(39,27,15),(47,35,19),(55,43,23),
    (63,47,23),(75,55,27),(83,59,27),(91,67,31),(99,75,31),(107,83,31),
    (115,87,31),(123,95,35),(131,103,35),(143,111,35),(11,11,15),(19,19,27),
    (27,27,39),(39,39,51),(47,47,63),(55,55,75),(63,63,87),(71,71,103),
    (79,79,115),(91,91,127),(99,99,139),(107,107,151),(115,115,163),
    (123,123,175),(131,131,187),(139,139,203),(0,0,0),(7,7,0),(11,11,0),
    (19,19,0),(27,27,0),(35,35,0),(43,43,7),(47,47,7),(55,55,7),(63,63,7),
    (71,71,7),(75,75,11),(83,83,11),(91,91,11),(99,99,11),(107,107,15),
    (7,0,0),(15,0,0),(23,0,0),(31,0,0),(39,0,0),(47,0,0),(55,0,0),(63,0,0),
    (71,0,0),(79,0,0),(87,0,0),(95,0,0),(103,0,0),(111,0,0),(119,0,0),
    (127,0,0),(19,19,0),(27,27,0),(35,35,0),(47,43,0),(55,47,0),(67,55,0),
    (75,59,7),(87,67,7),(95,71,7),(107,75,11),(119,83,15),(131,87,19),
    (139,91,19),(151,95,27),(163,99,31),(175,103,35),(35,19,7),(47,23,11),
    (59,31,15),(75,35,19),(87,43,23),(99,47,31),(115,55,35),(127,59,43),
    (143,67,51),(159,79,51),(175,99,47),(191,119,47),(207,143,43),
    (223,171,39),(239,203,31),(255,243,27),(11,7,0),(27,19,0),(43,35,15),
    (55,43,19),(71,51,27),(83,55,35),(99,63,43),(111,71,51),(127,83,63),
    (139,95,71),(155,107,83),(167,123,95),(183,135,107),(195,147,123),
    (211,163,139),(227,179,151),(171,139,163),(159,127,151),(147,115,135),
    (139,103,123),(127,91,111),(119,83,99),(107,75,87),(95,63,75),
    (87,55,67),(75,47,55),(67,39,47),(55,31,35),(43,23,27),(35,19,19),
    (23,11,11),(15,7,7),(187,115,159),(175,107,143),(163,95,131),
    (151,87,119),(139,79,107),(127,75,95),(115,67,83),(107,59,75),
    (95,51,63),(83,43,55),(71,35,43),(59,31,35),(47,23,27),(35,19,19),
    (23,11,11),(15,7,7),(219,195,187),(203,179,167),(191,163,155),
    (175,151,139),(163,135,123),(151,123,111),(135,111,95),(123,99,83),
    (107,87,71),(95,75,59),(83,63,51),(67,51,39),(55,43,31),(39,31,23),
    (27,19,15),(15,11,7),(111,131,123),(103,123,111),(95,115,103),
    (87,107,95),(79,99,87),(71,91,79),(63,83,71),(55,75,63),(47,67,55),
    (43,59,47),(35,51,39),(31,43,31),(23,35,23),(15,27,19),(11,19,11),
    (7,11,7),(255,243,27),(239,223,19),(219,203,15),(203,183,11),
    (187,167,7),(171,151,7),(155,131,7),(139,115,7),(123,99,7),(107,83,0),
    (91,71,0),(75,55,0),(59,43,0),(43,31,0),(27,15,0),(11,7,0),
    (0,0,255),(11,11,239),(19,19,223),(27,27,207),(35,35,191),(43,43,175),
    (47,47,159),(47,47,143),(47,47,127),(47,47,111),(47,47,95),(43,43,79),
    (35,35,63),(27,27,47),(19,19,31),(11,11,15),(43,0,0),(59,0,0),
    (75,7,0),(95,7,0),(111,15,0),(127,23,7),(147,31,7),(163,39,11),
    (183,51,15),(195,75,27),(207,99,43),(219,127,59),(227,151,79),
    (231,171,95),(239,191,119),(247,211,139),(167,123,59),(183,155,55),
    (199,195,55),(231,227,87),(127,191,255),(171,231,255),(215,255,255),
    (103,0,0),(139,0,0),(179,0,0),(215,0,0),(255,0,0),(255,243,147),
    (255,247,199),(255,255,255),(159,91,83),
]

# Pad palette to 256 entries if needed
while len(_QUAKE_PALETTE) < 256:
    _QUAKE_PALETTE.append((0, 0, 0))

WAD2_MAGIC = b"WAD2"

_DIR_ENTRY_STRUCT = struct.Struct("<iii2xBB16s")  # offset, disk_size, size, type, compression, name


class WadFormatError(Exception):
    """Raised when a WAD file is malformed."""


@dataclass(slots=True)
class WadTexture:
    name: str
    width: int
    height: int
    pixels: bytes  # raw indexed pixel data (palette indices)


@dataclass(slots=True)
class WadInfo:
    textures: list[WadTexture] = field(default_factory=list)


def read_wad(path: Path) -> WadInfo:
    """Read textures from a Quake WAD2 file."""
    data = path.read_bytes()

    if len(data) < 12:
        raise WadFormatError("File too small to be a valid WAD")

    magic = data[:4]
    if magic != WAD2_MAGIC:
        raise WadFormatError(f"Invalid WAD magic: {magic!r} (expected {WAD2_MAGIC!r})")

    num_entries, dir_offset = struct.unpack_from("<ii", data, 4)

    info = WadInfo()

    for i in range(num_entries):
        entry_offset = dir_offset + i * 32
        if entry_offset + 32 > len(data):
            break

        offset, disk_size, size, entry_type, _compression, name_raw = (
            _DIR_ENTRY_STRUCT.unpack_from(data, entry_offset)
        )

        name = name_raw.split(b"\x00", 1)[0].decode("ascii", errors="replace")

        # Type 0x44 = 'D' = MIP texture
        if entry_type != 0x44:
            continue

        if offset + 40 > len(data):
            continue

        # MIP texture header: 16-byte name, width, height, 4 mip offsets
        tex_name_raw = data[offset:offset + 16]
        tex_name = tex_name_raw.split(b"\x00", 1)[0].decode("ascii", errors="replace")
        width, height = struct.unpack_from("<II", data, offset + 16)

        mip0_offset = struct.unpack_from("<I", data, offset + 24)[0]
        pixel_count = width * height
        pixel_start = offset + mip0_offset

        if pixel_start + pixel_count > len(data):
            continue

        pixels = data[pixel_start:pixel_start + pixel_count]

        info.textures.append(WadTexture(
            name=tex_name or name,
            width=width,
            height=height,
            pixels=pixels,
        ))

    return info


def texture_to_rgb(texture: WadTexture) -> bytes:
    """Convert indexed texture pixels to RGB bytes using the Quake palette."""
    result = bytearray(len(texture.pixels) * 3)
    for i, idx in enumerate(texture.pixels):
        r, g, b = _QUAKE_PALETTE[idx]
        result[i * 3] = r
        result[i * 3 + 1] = g
        result[i * 3 + 2] = b
    return bytes(result)
