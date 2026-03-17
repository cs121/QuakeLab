from __future__ import annotations

import shutil
from pathlib import Path

from PySide6.QtCore import QMimeData, QPoint, Qt, Signal
from PySide6.QtGui import QDragEnterEvent, QDragMoveEvent, QDropEvent
from PySide6.QtWidgets import (
    QFileSystemModel,
    QMenu,
    QMessageBox,
    QTreeView,
)


class SourceTreeView(QTreeView):
    """Tree view for source files with drag & drop, context menu, and double-click support."""

    # Emitted when user wants to open a .map file in TrenchBroom
    open_in_trenchbroom = Signal(Path)
    # Emitted when user wants to compile a .map file directly
    compile_map_requested = Signal(Path)
    # Emitted when user wants to delete a path
    delete_requested = Signal(Path)
    # Emitted when user wants to rename a path
    rename_requested = Signal(Path)
    # Emitted when user wants to create a new entry inside a directory
    new_entry_requested = Signal(Path)  # Path is the target directory

    def __init__(self, parent=None) -> None:
        super().__init__(parent)
        self._source_root = Path(".")
        self.setAcceptDrops(True)
        self.setDragEnabled(True)
        self.setDropIndicatorShown(True)
        self.setDragDropMode(QTreeView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)

    def configure_root(self, source_root: Path) -> None:
        self._source_root = source_root.resolve()

    # ------------------------------------------------------------------
    # Double-click: open .map files in TrenchBroom
    # ------------------------------------------------------------------

    def mouseDoubleClickEvent(self, event) -> None:
        index = self.indexAt(event.position().toPoint())
        if index.isValid():
            model = self.model()
            if isinstance(model, QFileSystemModel):
                path = Path(model.filePath(index))
                if path.is_file() and path.suffix.lower() == ".map":
                    self.open_in_trenchbroom.emit(path)
                    return
        super().mouseDoubleClickEvent(event)

    # ------------------------------------------------------------------
    # Context menu
    # ------------------------------------------------------------------

    def _show_context_menu(self, pos: QPoint) -> None:
        index = self.indexAt(pos)
        model = self.model()
        if not isinstance(model, QFileSystemModel):
            return

        path: Path | None = None
        if index.isValid():
            path = Path(model.filePath(index))

        menu = QMenu(self)

        if path is not None and path.is_file():
            # .map-specific actions
            if path.suffix.lower() == ".map":
                tb_action = menu.addAction("Open in TrenchBroom")
                tb_action.triggered.connect(lambda: self.open_in_trenchbroom.emit(path))
                compile_action = menu.addAction("Compile Map")
                compile_action.triggered.connect(lambda: self.compile_map_requested.emit(path))
                menu.addSeparator()

            rename_action = menu.addAction("Rename…")
            rename_action.triggered.connect(lambda: self.rename_requested.emit(path))
            delete_action = menu.addAction("Delete")
            delete_action.triggered.connect(lambda: self.delete_requested.emit(path))

        elif path is not None and path.is_dir():
            new_action = menu.addAction("New File / Folder…")
            new_action.triggered.connect(lambda: self.new_entry_requested.emit(path))
            menu.addSeparator()
            rename_action = menu.addAction("Rename…")
            rename_action.triggered.connect(lambda: self.rename_requested.emit(path))
            if path.resolve() != self._source_root:
                delete_action = menu.addAction("Delete Folder")
                delete_action.triggered.connect(lambda: self.delete_requested.emit(path))

        else:
            # Right-clicked on empty space → root-level new entry
            new_action = menu.addAction("New File / Folder…")
            new_action.triggered.connect(lambda: self.new_entry_requested.emit(self._source_root))

        if not menu.isEmpty():
            menu.exec(self.viewport().mapToGlobal(pos))

    # ------------------------------------------------------------------
    # Drag & drop
    # ------------------------------------------------------------------

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
