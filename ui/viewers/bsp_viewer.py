from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QLabel,
    QPlainTextEdit,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from infrastructure.formats.bsp import BspFormatError, BspInfo, read_bsp_info
from ui.viewers.base import PreviewHandler


class BspPreviewHandler(PreviewHandler):
    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() == ".bsp"

    def create_widget(self, path: Path) -> QWidget:
        try:
            info = read_bsp_info(path)
        except (BspFormatError, OSError) as exc:
            label = QLabel(f"Could not read BSP file:\n{exc}")
            return label

        tabs = QTabWidget()
        tabs.addTab(self._summary_tab(info, path), "Summary")
        tabs.addTab(self._entities_tab(info), "Entities")
        tabs.addTab(self._textures_tab(info), "Textures")
        return tabs

    def _summary_tab(self, info: BspInfo, path: Path) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        rows = [
            ("File", path.name),
            ("BSP Version", str(info.version)),
            ("Entities", str(info.entity_count)),
            ("Textures", str(len(info.texture_names))),
            ("Faces", str(info.face_count)),
            ("Models", str(info.model_count)),
        ]
        # Add lump sizes
        for lump_name, size in info.lump_sizes.items():
            rows.append((f"Lump: {lump_name}", f"{size:,} bytes"))

        table = QTableWidget(len(rows), 2)
        table.setHorizontalHeaderLabels(["Property", "Value"])
        for i, (key, val) in enumerate(rows):
            table.setItem(i, 0, QTableWidgetItem(key))
            table.setItem(i, 1, QTableWidgetItem(val))
        table.resizeColumnsToContents()
        layout.addWidget(table)
        return w

    def _entities_tab(self, info: BspInfo) -> QWidget:
        edit = QPlainTextEdit()
        edit.setReadOnly(True)
        edit.setPlainText(info.raw_entities if info.raw_entities else "(no entities)")
        return edit

    def _textures_tab(self, info: BspInfo) -> QWidget:
        if not info.texture_names:
            return QLabel("(no textures)")
        table = QTableWidget(len(info.texture_names), 1)
        table.setHorizontalHeaderLabels(["Texture Name"])
        for i, name in enumerate(info.texture_names):
            table.setItem(i, 0, QTableWidgetItem(name))
        table.resizeColumnsToContents()
        return table
