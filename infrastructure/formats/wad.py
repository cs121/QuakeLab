"""WAD2 file parser (Quake texture/lump archive format)."""
from __future__ import annotations

import struct
from dataclasses import dataclass, field
from pathlib import Path


MAGIC_WAD2 = b"WAD2"
MAGIC_WAD3 = b"WAD3"

# Lump type codes
TYPE_PALETTE   = 0x40  # '@'  raw colour map (256×64)
TYPE_BSP_LUMP  = 0x42  # 'B'  embedded BSP lump
TYPE_MIPTEX    = 0x44  # 'D'  mipmapped texture
TYPE_QPIC      = 0x47  # 'G'  flat picture (status bar gfx)


@dataclass
class WadEntry:
    name: str
    offset: int
    size: int
    entry_type: int          # raw byte type code
    compressed: bool = False

    @property
    def type_label(self) -> str:
        labels = {
            TYPE_PALETTE: "Palette",
            TYPE_BSP_LUMP: "BSP Lump",
            TYPE_MIPTEX: "MipTex",
            TYPE_QPIC: "QPic",
        }
        return labels.get(self.entry_type, f"0x{self.entry_type:02X}")


@dataclass
class WadFile:
    magic: str
    entries: list[WadEntry] = field(default_factory=list)


@dataclass
class MipTex:
    name: str
    width: int
    height: int
    pixels: bytes       # mip level 0 (width × height palette indices)


@dataclass
class QPic:
    width: int
    height: int
    pixels: bytes       # width × height palette indices


class WadError(Exception):
    pass


def read_wad(path: Path) -> WadFile:
    """Parse a WAD2/WAD3 archive and return its directory."""
    data = path.read_bytes()
    if len(data) < 12:
        raise WadError("File too small to be a WAD archive")

    magic = data[:4]
    if magic not in (MAGIC_WAD2, MAGIC_WAD3):
        raise WadError(f"Not a WAD2/WAD3 file (magic={data[:4]!r})")

    num_lumps, dir_offset = struct.unpack_from("<ii", data, 4)
    if dir_offset < 0 or dir_offset + num_lumps * 32 > len(data):
        raise WadError("WAD directory out of bounds")

    wad = WadFile(magic=magic.decode("ascii", errors="replace"))
    for i in range(num_lumps):
        base = dir_offset + i * 32
        offset, csize, size, ltype, compression, _pad = struct.unpack_from("<iiiBBH", data, base)
        raw_name = data[base + 16: base + 32]
        name = raw_name.split(b"\x00")[0].decode("ascii", errors="replace")
        wad.entries.append(
            WadEntry(
                name=name,
                offset=offset,
                size=size,
                entry_type=ltype,
                compressed=(compression != 0),
            )
        )
    return wad


def read_miptex(data: bytes, entry: WadEntry) -> MipTex:
    """Extract a MIPTEX lump from raw WAD bytes."""
    base = entry.offset
    if base + 40 > len(data):
        raise WadError("MipTex lump out of bounds")

    raw_name = data[base: base + 16].split(b"\x00")[0].decode("ascii", errors="replace")
    width, height = struct.unpack_from("<II", data, base + 16)
    mip0_off = struct.unpack_from("<I", data, base + 24)[0]

    if width == 0 or height == 0 or width > 4096 or height > 4096:
        raise WadError(f"Invalid MipTex dimensions {width}×{height}")

    pixel_start = base + mip0_off
    pixel_count = width * height
    if pixel_start + pixel_count > len(data):
        raise WadError("MipTex pixel data out of bounds")

    return MipTex(
        name=raw_name,
        width=width,
        height=height,
        pixels=data[pixel_start: pixel_start + pixel_count],
    )


def read_qpic(data: bytes, entry: WadEntry) -> QPic:
    """Extract a QPic (flat image) lump from raw WAD bytes."""
    base = entry.offset
    if base + 8 > len(data):
        raise WadError("QPic lump out of bounds")

    width, height = struct.unpack_from("<II", data, base)
    pixel_count = width * height
    if pixel_count == 0 or width > 4096 or height > 4096:
        raise WadError(f"Invalid QPic dimensions {width}×{height}")

    pixel_start = base + 8
    if pixel_start + pixel_count > len(data):
        raise WadError("QPic pixel data out of bounds")

    return QPic(width=width, height=height, pixels=data[pixel_start: pixel_start + pixel_count])
