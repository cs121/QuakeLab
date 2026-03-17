"""Shared Quake palette loader used by WAD, LMP, MDL and SPR viewers."""
from __future__ import annotations

from pathlib import Path


def load_palette(source_root: Path | None = None) -> list[tuple[int, int, int]]:
    """Return a 256-entry Quake RGB palette.

    Search order:
      1. <source_root>/gfx/palette.lmp
      2. <source_root>/palette.lmp
      3. Built-in 6×6×6 colour cube + 40 grayscale steps (rough approximation).
    """
    if source_root is not None:
        for candidate in [
            source_root / "gfx" / "palette.lmp",
            source_root / "palette.lmp",
        ]:
            if candidate.is_file():
                data = candidate.read_bytes()
                if len(data) >= 768:
                    return [(data[i * 3], data[i * 3 + 1], data[i * 3 + 2]) for i in range(256)]

    # Fallback: 6×6×6 colour cube (216 entries) + 40 grayscale steps
    pal: list[tuple[int, int, int]] = []
    for r in range(6):
        for g in range(6):
            for b in range(6):
                pal.append((r * 51, g * 51, b * 51))
    for i in range(40):
        v = min(255, i * 6)
        pal.append((v, v, v))
    while len(pal) < 256:
        pal.append((0, 0, 0))
    return pal


def palette_to_qimage_data(
    pixels: bytes | bytearray,
    width: int,
    height: int,
    palette: list[tuple[int, int, int]],
) -> bytes:
    """Convert palette-indexed pixel data to raw 32-bit ARGB bytes for QImage."""
    out = bytearray(width * height * 4)
    for i, idx in enumerate(pixels[: width * height]):
        r, g, b = palette[idx]
        base = i * 4
        out[base] = b
        out[base + 1] = g
        out[base + 2] = r
        out[base + 3] = 0xFF
    return bytes(out)
