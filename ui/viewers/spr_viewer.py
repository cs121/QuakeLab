"""Quake 1 SPR sprite viewer – metadata + frame preview."""
from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QLabel,
    QListWidget,
    QListWidgetItem,
    QScrollArea,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from infrastructure.formats.palette import load_palette, palette_to_qimage_data
from infrastructure.formats.spr import SprError, read_spr_info
from ui.viewers.base import PreviewHandler


class SprPreviewHandler(PreviewHandler):
    exts = {".spr"}

    def __init__(self, settings=None) -> None:
        self._settings = settings

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in self.exts

    def create_widget(self, path: Path) -> QWidget:
        try:
            info = read_spr_info(path)
        except (SprError, OSError) as exc:
            return QLabel(f"Cannot read SPR file:\n{exc}")

        source_root: Path | None = None
        if self._settings is not None:
            try:
                source_root = self._settings.source_root().resolve()
            except Exception:
                pass
        palette = load_palette(source_root)

        tabs = QTabWidget()
        tabs.addTab(self._summary_tab(info, path), "Summary")
        tabs.addTab(self._frames_tab(info, palette), "Frames")
        return tabs

    def _summary_tab(self, info, path: Path) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        rows = [
            ("File", path.name),
            ("Sprite Type", info.type_label),
            ("Max Size", f"{info.max_width} × {info.max_height}"),
            ("Frames", str(info.num_frames)),
            ("Parsed Frames", str(len(info.frames))),
            ("Bounding Radius", f"{info.bounding_radius:.3f}"),
        ]
        table = QTableWidget(len(rows), 2)
        table.setHorizontalHeaderLabels(["Property", "Value"])
        for i, (k, v) in enumerate(rows):
            table.setItem(i, 0, QTableWidgetItem(k))
            table.setItem(i, 1, QTableWidgetItem(v))
        table.resizeColumnsToContents()
        layout.addWidget(table)
        return w

    def _frames_tab(self, info, palette) -> QWidget:
        if not info.frames:
            return QLabel("No frame data could be parsed.")

        splitter = QSplitter(Qt.Orientation.Horizontal)

        lst = QListWidget()
        for i, frame in enumerate(info.frames):
            lst.addItem(QListWidgetItem(f"Frame {i}  ({frame.width}×{frame.height})"))

        meta_label = QLabel("")
        preview_label = QLabel("Select a frame")
        preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        preview_panel = QWidget()
        pv_layout = QVBoxLayout(preview_panel)
        pv_layout.addWidget(meta_label)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(preview_label)
        pv_layout.addWidget(scroll)

        def _on_select(row: int) -> None:
            if row < 0 or row >= len(info.frames):
                return
            frame = info.frames[row]
            raw = palette_to_qimage_data(frame.pixels, frame.width, frame.height, palette)
            img = QImage(raw, frame.width, frame.height, frame.width * 4, QImage.Format.Format_ARGB32)
            pix = QPixmap.fromImage(img)
            preview_label.setPixmap(pix)
            preview_label.setFixedSize(pix.size())
            meta_label.setText(
                f"Frame {row}  ·  {frame.width}×{frame.height} px  ·  "
                f"origin ({frame.origin_x}, {frame.origin_y})"
            )

        lst.currentRowChanged.connect(_on_select)
        if info.frames:
            lst.setCurrentRow(0)

        splitter.addWidget(lst)
        splitter.addWidget(preview_panel)
        splitter.setSizes([150, 650])
        return splitter
