from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import QPlainTextEdit

from ui.viewers.base import PreviewHandler


class TextPreviewHandler(PreviewHandler):
    exts = {".qc", ".txt", ".cfg", ".shader", ".map", ".src", ".md"}

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in self.exts

    def create_widget(self, path: Path) -> QPlainTextEdit:
        edit = QPlainTextEdit()
        edit.setReadOnly(True)
        edit.setPlainText(path.read_text(encoding="utf-8", errors="replace"))
        return edit
