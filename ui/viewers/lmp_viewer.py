from __future__ import annotations

import struct
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from ui.viewers.base import PreviewHandler


def _load_palette(source_root: Path | None) -> list[tuple[int, int, int]]:
    """Load a 256-color Quake palette.

    Searches for palette.lmp in the source root (gfx/palette.lmp or palette.lmp).
    Falls back to a 6x6x6 color cube + grayscale ramp as a rough approximation.
    """
    if source_root:
        for candidate in [source_root / "gfx" / "palette.lmp", source_root / "palette.lmp"]:
            if candidate.is_file():
                data = candidate.read_bytes()
                if len(data) >= 768:
                    return [(data[i * 3], data[i * 3 + 1], data[i * 3 + 2]) for i in range(256)]

    # Fallback: 6x6x6 color cube (216 entries) + 40 grayscale steps
    palette: list[tuple[int, int, int]] = []
    for r in range(6):
        for g in range(6):
            for b in range(6):
                palette.append((r * 51, g * 51, b * 51))
    for i in range(40):
        v = min(255, i * 6)
        palette.append((v, v, v))
    while len(palette) < 256:
        palette.append((0, 0, 0))
    return palette


def _render_lmp_image(
    width: int,
    height: int,
    pixels: bytes,
    palette: list[tuple[int, int, int]],
) -> QImage:
    """Render a palette-indexed LMP image to a QImage (RGB32)."""
    img = QImage(width, height, QImage.Format.Format_RGB32)
    for y in range(height):
        for x in range(width):
            idx = pixels[y * width + x]
            r, g, b = palette[idx]
            img.setPixel(x, y, (0xFF << 24) | (r << 16) | (g << 8) | b)
    return img


def _render_palette_swatches(palette: list[tuple[int, int, int]]) -> QImage:
    """Render a 16x16 grid of palette swatches (one per color)."""
    cell = 16
    img = QImage(16 * cell, 16 * cell, QImage.Format.Format_RGB32)
    for i, (r, g, b) in enumerate(palette):
        col = i % 16
        row = i // 16
        for dy in range(cell):
            for dx in range(cell):
                img.setPixel(col * cell + dx, row * cell + dy, (0xFF << 24) | (r << 16) | (g << 8) | b)
    return img


class LmpPreviewHandler(PreviewHandler):
    exts = {".lmp"}

    def __init__(self, settings=None) -> None:
        # settings may be None; used only to resolve source_root for palette.lmp lookup
        self._settings = settings

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in self.exts

    def create_widget(self, path: Path) -> QWidget:
        root = QWidget()
        layout = QVBoxLayout(root)

        source_root: Path | None = None
        if self._settings is not None:
            try:
                source_root = self._settings.source_root().resolve()
            except Exception:
                pass

        palette = _load_palette(source_root)
        palette_source = "project palette.lmp" if source_root and (
            (source_root / "gfx" / "palette.lmp").is_file()
            or (source_root / "palette.lmp").is_file()
        ) else "built-in fallback palette"

        data = path.read_bytes()
        file_size = len(data)

        # Detect palette.lmp itself: exactly 768 bytes, no image header needed
        if file_size == 768:
            meta = QLabel(f"Palette file (256 colors) · {file_size} bytes")
            layout.addWidget(meta)
            img = _render_palette_swatches([(data[i * 3], data[i * 3 + 1], data[i * 3 + 2]) for i in range(256)])
            label = QLabel()
            label.setAlignment(Qt.AlignmentFlag.AlignCenter)
            label.setPixmap(QPixmap.fromImage(img))
            area = QScrollArea()
            area.setWidgetResizable(True)
            area.setWidget(label)
            layout.addWidget(area)
            return root

        # Generic LMP image: 4-byte width + 4-byte height + pixel data
        if file_size < 8:
            layout.addWidget(QLabel(f"LMP file too small to parse ({file_size} bytes)"))
            return root

        width, height = struct.unpack_from("<ii", data, 0)
        pixel_count = width * height

        if width <= 0 or height <= 0 or pixel_count > 4_000_000 or 8 + pixel_count > file_size:
            layout.addWidget(QLabel(
                f"Cannot parse LMP as image (w={width}, h={height}, file={file_size} bytes).\n"
                "File may be a raw data lump without an image header."
            ))
            hex_preview = " ".join(f"{b:02x}" for b in data[:64])
            layout.addWidget(QLabel(f"First 64 bytes:\n{hex_preview}"))
            return root

        pixels = data[8: 8 + pixel_count]
        img = _render_lmp_image(width, height, pixels, palette)

        meta = QLabel(
            f"{width} × {height} px · {file_size} bytes · palette: {palette_source}"
        )
        layout.addWidget(meta)

        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setPixmap(QPixmap.fromImage(img))

        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(label)
        layout.addWidget(area)
        return root
