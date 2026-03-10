from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QLabel

from ui.viewers.base import PreviewHandler


class FallbackPreviewHandler(PreviewHandler):
    def can_handle(self, path: Path) -> bool:
        return True

    def create_widget(self, path: Path) -> QLabel:
        size = path.stat().st_size if path.exists() else 0
        return QLabel(f"No dedicated preview for: {path.name}\nSize: {size} bytes")
