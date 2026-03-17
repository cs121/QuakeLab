from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from ui.viewers.base import PreviewHandler


class EditableTextWidget(QWidget):
    """Text editor with save button and unsaved-changes indicator."""

    def __init__(self, path: Path, parent=None) -> None:
        super().__init__(parent)
        self._path = path
        self._saved = True

        self._editor = QPlainTextEdit()
        self._editor.setPlainText(path.read_text(encoding="utf-8", errors="replace"))
        self._editor.textChanged.connect(self._mark_dirty)

        self._status = QLabel("")
        self._save_btn = QPushButton("Save")
        self._save_btn.clicked.connect(self._save)
        self._save_btn.setEnabled(False)

        btn_row = QHBoxLayout()
        btn_row.addWidget(self._status)
        btn_row.addStretch(1)
        btn_row.addWidget(self._save_btn)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self._editor, stretch=1)
        layout.addLayout(btn_row)

    def _mark_dirty(self) -> None:
        if self._saved:
            self._saved = False
            self._status.setText("● Unsaved changes")
            self._status.setStyleSheet("color: orange; font-weight: bold;")
            self._save_btn.setEnabled(True)

    def _save(self) -> None:
        try:
            self._path.write_text(self._editor.toPlainText(), encoding="utf-8")
            self._saved = True
            self._status.setText("Saved")
            self._status.setStyleSheet("color: green;")
            self._save_btn.setEnabled(False)
        except OSError as exc:
            QMessageBox.warning(self, "Save", f"Could not save file:\n{exc}")

    # Allow external code to access the underlying editor (e.g. for cursor positioning)
    def document(self):
        return self._editor.document()

    def setTextCursor(self, cursor):
        self._editor.setTextCursor(cursor)

    def centerCursor(self):
        self._editor.centerCursor()


class TextPreviewHandler(PreviewHandler):
    exts = {".qc", ".txt", ".cfg", ".shader", ".map", ".src", ".md"}

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in self.exts

    def create_widget(self, path: Path) -> QWidget:
        return EditableTextWidget(path)
