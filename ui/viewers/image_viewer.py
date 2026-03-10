from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QLabel, QScrollArea, QVBoxLayout, QWidget

from ui.viewers.base import PreviewHandler


class ImagePreviewHandler(PreviewHandler):
    exts = {".png", ".jpg", ".jpeg", ".bmp", ".tga"}

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in self.exts

    def create_widget(self, path: Path) -> QWidget:
        root = QWidget()
        layout = QVBoxLayout(root)
        meta = QLabel()
        pix = QPixmap(str(path))
        meta.setText(f"{pix.width()}x{pix.height()} - {path.suffix.lower()}")
        label = QLabel()
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        label.setPixmap(pix)
        area = QScrollArea()
        area.setWidgetResizable(True)
        area.setWidget(label)
        layout.addWidget(meta)
        layout.addWidget(area)
        return root
