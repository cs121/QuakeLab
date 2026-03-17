"""WAD2/WAD3 texture archive viewer."""
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
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from infrastructure.formats.palette import load_palette, palette_to_qimage_data
from infrastructure.formats.wad import (
    TYPE_MIPTEX,
    TYPE_QPIC,
    TYPE_PALETTE,
    WadEntry,
    WadError,
    read_miptex,
    read_qpic,
    read_wad,
)
from ui.viewers.base import PreviewHandler


def _render_pixels(pixels: bytes, width: int, height: int, palette) -> QPixmap:
    raw = palette_to_qimage_data(pixels, width, height, palette)
    img = QImage(raw, width, height, width * 4, QImage.Format.Format_ARGB32)
    return QPixmap.fromImage(img)


class WadPreviewHandler(PreviewHandler):
    exts = {".wad"}

    def __init__(self, settings=None) -> None:
        self._settings = settings

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in self.exts

    def create_widget(self, path: Path) -> QWidget:
        try:
            wad = read_wad(path)
        except (WadError, OSError) as exc:
            return QLabel(f"Cannot read WAD file:\n{exc}")

        source_root: Path | None = None
        if self._settings is not None:
            try:
                source_root = self._settings.source_root().resolve()
            except Exception:
                pass
        palette = load_palette(source_root)

        raw_data = path.read_bytes()

        tabs = QTabWidget()
        tabs.addTab(self._directory_tab(wad, raw_data, palette, path), "Directory")
        tabs.addTab(self._textures_tab(wad, raw_data, palette), "Textures")
        return tabs

    # ------------------------------------------------------------------

    def _directory_tab(self, wad, raw_data: bytes, palette, path: Path) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        info = QLabel(
            f"Format: {wad.magic}  ·  Entries: {len(wad.entries)}  ·  File: {path.name}"
        )
        layout.addWidget(info)

        table = QTableWidget(len(wad.entries), 4)
        table.setHorizontalHeaderLabels(["Name", "Type", "Size", "Offset"])
        for i, entry in enumerate(wad.entries):
            table.setItem(i, 0, QTableWidgetItem(entry.name))
            table.setItem(i, 1, QTableWidgetItem(entry.type_label))
            table.setItem(i, 2, QTableWidgetItem(f"{entry.size:,}"))
            table.setItem(i, 3, QTableWidgetItem(f"0x{entry.offset:08X}"))
        table.resizeColumnsToContents()
        layout.addWidget(table)
        return w

    def _textures_tab(self, wad, raw_data: bytes, palette) -> QWidget:
        """Split pane: entry list on left, texture preview on right."""
        splitter = QSplitter(Qt.Orientation.Horizontal)

        lst = QListWidget()
        renderable = [e for e in wad.entries if e.entry_type in (TYPE_MIPTEX, TYPE_QPIC)]
        for entry in renderable:
            lst.addItem(QListWidgetItem(f"{entry.name}  [{entry.type_label}]"))

        preview_label = QLabel("Select a texture")
        preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        meta_label = QLabel("")
        preview_panel = QWidget()
        pv_layout = QVBoxLayout(preview_panel)
        pv_layout.addWidget(meta_label)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(preview_label)
        pv_layout.addWidget(scroll)

        def _on_select(row: int) -> None:
            if row < 0 or row >= len(renderable):
                return
            entry = renderable[row]
            try:
                if entry.entry_type == TYPE_MIPTEX:
                    tex = read_miptex(raw_data, entry)
                    pix = _render_pixels(tex.pixels, tex.width, tex.height, palette)
                    meta_label.setText(f"{tex.name}  {tex.width}×{tex.height}")
                elif entry.entry_type == TYPE_QPIC:
                    pic = read_qpic(raw_data, entry)
                    pix = _render_pixels(pic.pixels, pic.width, pic.height, palette)
                    meta_label.setText(f"{entry.name}  {pic.width}×{pic.height}")
                else:
                    return
                preview_label.setPixmap(pix)
                preview_label.setFixedSize(pix.size())
            except WadError as exc:
                preview_label.setText(f"Error: {exc}")
                preview_label.setPixmap(QPixmap())

        lst.currentRowChanged.connect(_on_select)

        splitter.addWidget(lst)
        splitter.addWidget(preview_panel)
        splitter.setSizes([200, 600])
        return splitter

        if not renderable:
            return QLabel("No renderable textures in this WAD file.")
        return splitter
