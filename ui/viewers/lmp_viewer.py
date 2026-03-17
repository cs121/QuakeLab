"""Quake LMP file viewer (palette-indexed images and palette files)."""
from __future__ import annotations

import struct
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from infrastructure.formats.palette import load_palette, palette_to_qimage_data
from ui.viewers.base import PreviewHandler


def _render_palette_swatches(palette: list[tuple[int, int, int]]) -> QImage:
    """16 × 16 grid of colour swatches, one per palette entry."""
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

        palette = load_palette(source_root)
        has_project_palette = source_root is not None and (
            (source_root / "gfx" / "palette.lmp").is_file()
            or (source_root / "palette.lmp").is_file()
        )
        palette_source = "project palette.lmp" if has_project_palette else "built-in fallback palette"

        data = path.read_bytes()
        file_size = len(data)

        # palette.lmp itself: exactly 768 bytes (256 × RGB)
        if file_size == 768:
            meta = QLabel(f"Palette file · 256 colours · {file_size} bytes")
            layout.addWidget(meta)
            pal = [(data[i * 3], data[i * 3 + 1], data[i * 3 + 2]) for i in range(256)]
            img = _render_palette_swatches(pal)
            lbl = QLabel()
            lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
            lbl.setPixmap(QPixmap.fromImage(img))
            area = QScrollArea()
            area.setWidgetResizable(True)
            area.setWidget(lbl)
            layout.addWidget(area)
            return root

        # Generic LMP image: int32 width + int32 height + pixel data
        if file_size < 8:
            layout.addWidget(QLabel(f"LMP file too small to parse ({file_size} bytes)"))
            return root

        width, height = struct.unpack_from("<ii", data, 0)
        pixel_count = width * height

        if width <= 0 or height <= 0 or pixel_count > 4_000_000 or 8 + pixel_count > file_size:
            layout.addWidget(QLabel(
                f"Cannot parse LMP as image (w={width}, h={height}, file={file_size} bytes).\n"
                "File may be a raw data lump without a standard image header."
            ))
            hex_preview = " ".join(f"{b:02x}" for b in data[:64])
            layout.addWidget(QLabel(f"First 64 bytes:\n{hex_preview}"))
            return root

        pixels = data[8: 8 + pixel_count]
        raw = palette_to_qimage_data(pixels, width, height, palette)
        img = QImage(raw, width, height, width * 4, QImage.Format.Format_ARGB32)

        meta = QLabel(f"{width} × {height} px · {file_size} bytes · palette: {palette_source}")
        layout.addWidget(meta)

        lbl = QLabel()
        lbl.setAlignment(Qt.AlignmentFlag.AlignCenter)
        lbl.setPixmap(QPixmap.fromImage(img))
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(lbl)
        layout.addWidget(area)
        return root
