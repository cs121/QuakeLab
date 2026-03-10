from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import QMimeData, QPoint, Qt
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import QFileSystemModel, QMessageBox, QTreeView


class SourceTreeView(QTreeView):
    """Tree view for source files with drag & drop support (internal + external)."""

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._source_root = Path(".")
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QTreeView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)

    def configure_root(self, source_root: Path) -> None:
        self._source_root = source_root.resolve()

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if self._has_supported_urls(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragEnterEvent(event)

    def dragMoveEvent(self, event: QDragMoveEvent) -> None:
        if self._has_supported_urls(event.mimeData()):
            event.acceptProposedAction()
            return
        super().dragMoveEvent(event)

    def dropEvent(self, event: QDropEvent) -> None:
        local_paths = self._extract_local_paths(event.mimeData())
        if not local_paths:
            super().dropEvent(event)
            return

        target = self._resolve_drop_target(event.position().toPoint())
        if target is None:
            event.ignore()
            return

        failed: list[str] = []
        for src in local_paths:
            ok, message = self._copy_or_move(src, target)
            if not ok:
                failed.append(f"{src.name}: {message}")

        if failed:
            QMessageBox.warning(self, "Drag & Drop", "\n".join(failed))

        event.acceptProposedAction()

    def _resolve_drop_target(self, drop_pos: QPoint) -> Path | None:
        model = self.model()
        if not isinstance(model, QFileSystemModel):
            return None

        index = self.indexAt(drop_pos)
        if not index.isValid():
            return self._source_root

        path = Path(model.filePath(index))
        return path if path.is_dir() else path.parent

    def _copy_or_move(self, source: Path, target_dir: Path) -> tuple[bool, str]:
        try:
            source = source.resolve()
            target_dir = target_dir.resolve()
            if not str(target_dir).startswith(str(self._source_root)):
                return False, "Ziel liegt außerhalb des Source-Ordners"

            destination = target_dir / source.name
            if destination.exists():
                return False, "Ziel existiert bereits"

            if str(source).startswith(str(self._source_root)):
                shutil.move(str(source), str(destination))
            elif source.is_dir():
                shutil.copytree(source, destination)
            else:
                target_dir.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source, destination)
        except Exception as exc:  # noqa: BLE001
            return False, str(exc)

        return True, ""

    @staticmethod
    def _extract_local_paths(mime: QMimeData) -> list[Path]:
        if not mime.hasUrls():
            return []

        paths: list[Path] = []
        for url in mime.urls():
            if url.isLocalFile():
                candidate = Path(url.toLocalFile())
                if candidate.exists():
                    paths.append(candidate)
        return paths

    @staticmethod
    def _has_supported_urls(mime: QMimeData) -> bool:
        return bool(SourceTreeView._extract_local_paths(mime))
