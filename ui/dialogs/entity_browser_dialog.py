from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QDialog,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QListWidget,
    QSplitter,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from core.parsers.def_parser import EntityDef, parse_def_file, parse_fgd_file


class EntityBrowserDialog(QDialog):
    def __init__(self, entity_def_path: str, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Entity Browser")
        self.resize(900, 600)

        self._defs: dict[str, EntityDef] = {}
        self._sorted_names: list[str] = []

        layout = QVBoxLayout(self)

        if not entity_def_path:
            layout.addWidget(QLabel("No entity definition file configured.\nSet 'entity_def_path' in Settings."))
            return

        path = Path(entity_def_path)
        if not path.exists():
            layout.addWidget(QLabel(f"Entity definition file not found:\n{path}"))
            return

        # Parse
        suffix = path.suffix.lower()
        if suffix == ".fgd":
            self._defs = parse_fgd_file(path)
        else:
            self._defs = parse_def_file(path)

        if not self._defs:
            layout.addWidget(QLabel(f"No entity definitions found in:\n{path}"))
            return

        self._sorted_names = sorted(self._defs.keys())

        # Search field
        self._search = QLineEdit()
        self._search.setPlaceholderText("Search entities...")
        self._search.textChanged.connect(self._filter)
        layout.addWidget(self._search)

        # Splitter: list | detail
        splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: entity list
        self._list = QListWidget()
        self._list.addItems(self._sorted_names)
        self._list.currentTextChanged.connect(self._show_entity)
        splitter.addWidget(self._list)

        # Right: detail panel
        detail = QWidget()
        detail_layout = QVBoxLayout(detail)
        detail_layout.setContentsMargins(4, 4, 4, 4)

        self._classname_label = QLabel()
        self._classname_label.setStyleSheet("font-size: 16px; font-weight: bold;")
        detail_layout.addWidget(self._classname_label)

        self._desc_label = QLabel()
        self._desc_label.setWordWrap(True)
        detail_layout.addWidget(self._desc_label)

        props_group = QGroupBox("Properties")
        props_layout = QVBoxLayout(props_group)
        self._props_table = QTableWidget(0, 2)
        self._props_table.setHorizontalHeaderLabels(["Key", "Description"])
        self._props_table.horizontalHeader().setStretchLastSection(True)
        props_layout.addWidget(self._props_table)
        detail_layout.addWidget(props_group)

        flags_group = QGroupBox("Spawnflags")
        flags_layout = QVBoxLayout(flags_group)
        self._flags_list = QListWidget()
        flags_layout.addWidget(self._flags_list)
        detail_layout.addWidget(flags_group)

        splitter.addWidget(detail)
        splitter.setSizes([250, 650])
        layout.addWidget(splitter)

        # Info bar
        info = QLabel(f"{len(self._defs)} entities loaded from {path.name}")
        info.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(info)

    def _filter(self, text: str) -> None:
        text = text.lower()
        self._list.clear()
        for name in self._sorted_names:
            if text in name.lower():
                self._list.addItem(name)

    def _show_entity(self, name: str) -> None:
        if not name or name not in self._defs:
            return
        ent = self._defs[name]
        self._classname_label.setText(ent.classname)
        self._desc_label.setText(ent.description or "(no description)")

        self._props_table.setRowCount(len(ent.properties))
        for i, (key, desc) in enumerate(ent.properties.items()):
            self._props_table.setItem(i, 0, QTableWidgetItem(key))
            self._props_table.setItem(i, 1, QTableWidgetItem(desc))

        self._flags_list.clear()
        self._flags_list.addItems(ent.flags)
