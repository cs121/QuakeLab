from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (
    QGridLayout,
    QLabel,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from infrastructure.formats.wad import WadFormatError, WadTexture, read_wad, texture_to_rgb
from ui.viewers.base import PreviewHandler


class WadPreviewHandler(PreviewHandler):
    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() == ".wad"

    def create_widget(self, path: Path) -> QWidget:
        try:
            info = read_wad(path)
        except (WadFormatError, OSError) as exc:
            return QLabel(f"Could not read WAD file:\n{exc}")

        if not info.textures:
            return QLabel("WAD file contains no textures.")

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        content = QWidget()
        grid = QGridLayout(content)

        cols = 4
        for i, tex in enumerate(info.textures):
            row, col = divmod(i, cols)
            cell = self._texture_cell(tex)
            grid.addWidget(cell, row, col)

        scroll.setWidget(content)

        wrapper = QWidget()
        layout = QVBoxLayout(wrapper)
        layout.setContentsMargins(0, 0, 0, 0)
        header = QLabel(f"{path.name}: {len(info.textures)} texture(s)")
        header.setStyleSheet("font-weight: bold;")
        layout.addWidget(header)
        layout.addWidget(scroll)
        return wrapper

    def _texture_cell(self, tex: WadTexture) -> QWidget:
        cell = QWidget()
        layout = QVBoxLayout(cell)
        layout.setContentsMargins(4, 4, 4, 4)

        # Convert to QImage
        rgb_data = texture_to_rgb(tex)
        image = QImage(rgb_data, tex.width, tex.height, tex.width * 3, QImage.Format.Format_RGB888)
        pixmap = QPixmap.fromImage(image)

        # Scale up small textures for visibility (max 128px)
        display_size = min(max(tex.width, tex.height, 64), 128)
        scaled = pixmap.scaled(display_size, display_size, Qt.AspectRatioMode.KeepAspectRatio)

        img_label = QLabel()
        img_label.setPixmap(scaled)
        img_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(img_label)

        name_label = QLabel(f"{tex.name}\n{tex.width}x{tex.height}")
        name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        name_label.setStyleSheet("font-size: 10px;")
        layout.addWidget(name_label)

        return cell
