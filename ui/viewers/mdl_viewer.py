"""Quake 1 MDL model viewer – metadata + skin texture preview."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QLabel,
    QScrollArea,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from infrastructure.formats.mdl import MdlError, read_mdl_info
from infrastructure.formats.palette import load_palette, palette_to_qimage_data
from ui.viewers.base import PreviewHandler


class MdlPreviewHandler(PreviewHandler):
    exts = {".mdl"}

    def __init__(self, settings=None) -> None:
        self._settings = settings

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in self.exts

    def create_widget(self, path: Path) -> QWidget:
        try:
            info = read_mdl_info(path)
        except (MdlError, OSError) as exc:
            return QLabel(f"Cannot read MDL file:\n{exc}")

        source_root: Path | None = None
        if self._settings is not None:
            try:
                source_root = self._settings.source_root().resolve()
            except Exception:
                pass
        palette = load_palette(source_root)

        tabs = QTabWidget()
        tabs.addTab(self._summary_tab(info, path), "Summary")
        tabs.addTab(self._skin_tab(info, palette), "Skin")
        return tabs

    def _summary_tab(self, info, path: Path) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        rows = [
            ("File", path.name),
            ("Skins", str(info.num_skins)),
            ("Skin Size", f"{info.skin_width} × {info.skin_height}"),
            ("Vertices", str(info.num_verts)),
            ("Triangles", str(info.num_tris)),
            ("Frames", str(info.num_frames)),
            ("Flags", f"0x{info.flags:04X}"),
            ("Bounding Radius", f"{info.bounding_radius:.3f}"),
            ("Scale", f"{info.scale[0]:.4f}, {info.scale[1]:.4f}, {info.scale[2]:.4f}"),
            ("Translate", f"{info.translate[0]:.4f}, {info.translate[1]:.4f}, {info.translate[2]:.4f}"),
        ]
        table = QTableWidget(len(rows), 2)
        table.setHorizontalHeaderLabels(["Property", "Value"])
        for i, (k, v) in enumerate(rows):
            table.setItem(i, 0, QTableWidgetItem(k))
            table.setItem(i, 1, QTableWidgetItem(v))
        table.resizeColumnsToContents()
        layout.addWidget(table)
        return w

    def _skin_tab(self, info, palette) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        if not info.first_skin_pixels:
            layout.addWidget(QLabel("No skin data available (group skin or parse error)."))
            return w

        raw = palette_to_qimage_data(info.first_skin_pixels, info.skin_width, info.skin_height, palette)
        img = QImage(raw, info.skin_width, info.skin_height, info.skin_width * 4, QImage.Format.Format_ARGB32)
        pix = QPixmap.fromImage(img)

        meta = QLabel(f"Skin 0 · {info.skin_width} × {info.skin_height} px")
        layout.addWidget(meta)

        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setPixmap(pix)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(label)
        layout.addWidget(scroll)
        return w
