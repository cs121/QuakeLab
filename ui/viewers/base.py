from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QWidget


class PreviewHandler:
    def can_handle(self, path: Path) -> bool:
        raise NotImplementedError

    def create_widget(self, path: Path) -> QWidget:
        raise NotImplementedError
