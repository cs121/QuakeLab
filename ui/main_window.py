from __future__ import annotations

from pathlib import Path
import shutil

from PySide6.QtCore import QObject, QTimer, Qt, Signal
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QFileSystemModel,
    QFrame,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QStatusBar,
    QTabWidget,
    QTableWidget,
    QTableWidgetItem,
    QTreeView,
    QVBoxLayout,
    QWidget,
)

from core.models.domain import BuildAction, CompilerDiagnostic
from core.parsers.qc_error_parser import parse_diagnostics
from core.services.build_queue_service import BuildQueueService
from core.services.change_journal_service import ChangeJournalService
from core.services.compiler_service import CompilerService
from core.services.deploy_service import DeployService
from core.services.launch_service import LaunchService
from core.services.log_service import LogService
from core.services.rebuild_service import RebuildService
from core.services.template_service import TemplateService
from core.services.validation_service import ValidationService
from core.services.pack_service import PackService
from core.services.preview_service import PreviewService
from core.services.project_service import ProjectService
from core.services.settings_service import SettingsService
from infrastructure.archives.pak import PakArchive, PakError
from infrastructure.filesystem.watcher import PollingWatchService
from ui.dialogs.settings_dialog import SettingsDialog
from ui.panels.source_tree import SourceTreeView


class _LineBridge(QObject):
    """Thread-safe bridge: emits a Qt signal for each line from a background thread."""
    line_received = Signal(str, str)  # (stream_name, text)


def build_pak_tree(paths: list[tuple[str, int]]) -> dict[str, dict]:
    tree: dict[str, dict] = {}
    for pak_path, size in paths:
        parts = [part for part in pak_path.split("/") if part]
        if not parts:
            continue
        node = tree
        for folder in parts[:-1]:
            node = node.setdefault(folder, {"_children": {}})["_children"]
        node[parts[-1]] = {"_size": size}
    return tree


class MainWindow(QMainWindow):
    def __init__(
        self,
        project_service: ProjectService,
        settings_service: SettingsService,
        change_journal: ChangeJournalService,
        build_queue: BuildQueueService,
        compiler_service: CompilerService,
        pack_service: PackService,
        deploy_service: DeployService,
        launch_service: LaunchService,
        rebuild_service: RebuildService,
        validation_service: ValidationService,
        template_service: TemplateService,
        watch_service: PollingWatchService,
        preview_service: PreviewService,
        log_service: LogService,
    ) -> None:
        super().__init__()
        self.project_service = project_service
        self.settings = settings_service
        self.change_journal = change_journal
        self.build_queue = build_queue
        self.compiler = compiler_service
        self.pack = pack_service
        self.deploy = deploy_service
        self.launch = launch_service
        self.rebuild = rebuild_service
        self.validation = validation_service
        self.templates = template_service
        self.watch = watch_service
        self.preview = preview_service
        self.logs = log_service
        self.pak_archive = PakArchive()
        self._pak_tree_model = QStandardItemModel(self)
        self._last_pak_signature: tuple[bool, int, int] | None = None
        self._diagnostics: list[CompilerDiagnostic] = []

        self.setWindowTitle("QuakeLab Workbench V1")
        self.resize(1400, 900)
        self._build_ui()
        self._init_timer()

    def _build_ui(self) -> None:
        self._build_menu()

        self.source_model = QFileSystemModel(self)
        self.source_model.setReadOnly(False)
        self.source_tree_title = QLabel("Source")
        self.source_tree_title.setToolTip("Displays source assets and editable files")
        self.source_tree = SourceTreeView()
        self.source_tree.setModel(self.source_model)
        self.source_tree.clicked.connect(self._source_clicked)

        source_actions = QWidget()
        source_action_layout = QHBoxLayout(source_actions)
        source_action_layout.setContentsMargins(0, 0, 0, 0)

        self.new_source_btn = QPushButton("Neu")
        self.new_source_btn.clicked.connect(self._create_source_entry)
        source_action_layout.addWidget(self.new_source_btn)

        self.rename_source_btn = QPushButton("edit")
        self.rename_source_btn.clicked.connect(self._rename_source_entry)
        source_action_layout.addWidget(self.rename_source_btn)

        self.delete_source_btn = QPushButton("löschen")
        self.delete_source_btn.clicked.connect(self._delete_source_entry)
        source_action_layout.addWidget(self.delete_source_btn)

        self.build_model = QFileSystemModel(self)
        self.build_tree_title = QLabel("Build / PAK")
        self.build_tree_title.setToolTip("Displays PAK file and its folder/file contents")
        self.build_tree = QTreeView()
        self.build_tree.setModel(self._pak_tree_model)

        source_panel = QWidget()
        source_layout = QVBoxLayout(source_panel)
        source_layout.setContentsMargins(0, 0, 0, 0)
        source_layout.addWidget(self.source_tree_title)
        source_layout.addWidget(source_actions)
        source_layout.addWidget(self.source_tree)

        build_panel = QWidget()
        build_layout = QVBoxLayout(build_panel)
        build_layout.setContentsMargins(0, 0, 0, 0)
        build_layout.addWidget(self.build_tree_title)
        build_layout.addWidget(self.build_tree)

        left_split = QSplitter()
        left_split.setOrientation(Qt.Orientation.Vertical)
        left_split.addWidget(source_panel)
        left_split.addWidget(build_panel)

        self.preview_container = QWidget()
        self.preview_layout = QVBoxLayout(self.preview_container)
        self.preview_context = QLabel("Window info: select an item in Source or Build / PAK")
        self.preview_context.setFrameStyle(QFrame.Shape.StyledPanel | QFrame.Shadow.Sunken)
        self.preview_layout.addWidget(self.preview_context)
        self.preview_body = QWidget()
        self.preview_body_layout = QVBoxLayout(self.preview_body)
        self.preview_body_layout.setContentsMargins(0, 0, 0, 0)
        self.preview_body_layout.addWidget(QLabel("Select a file for preview"))
        self.preview_layout.addWidget(self.preview_body)

        top_split = QSplitter()
        top_split.addWidget(left_split)
        top_split.addWidget(self.preview_container)
        top_split.setSizes([500, 900])

        self.change_table = QTableWidget(0, 5)
        self.change_table.setHorizontalHeaderLabels(["Time", "Type", "Path", "Hash", "Notes"])
        self.queue_table = QTableWidget(0, 4)
        self.queue_table.setHorizontalHeaderLabels(["Time", "Action", "Path", "Status"])
        self.log_table = QTableWidget(0, 4)
        self.log_table.setHorizontalHeaderLabels(["Time", "Level", "Source", "Message"])
        self.error_table = QTableWidget(0, 4)
        self.error_table.setHorizontalHeaderLabels(["File", "Line", "Severity", "Message"])
        self.error_table.cellDoubleClicked.connect(self._error_double_clicked)

        self.build_output = QPlainTextEdit()
        self.build_output.setReadOnly(True)
        self.build_output.setMaximumBlockCount(5000)

        self._line_bridge = _LineBridge()
        self._line_bridge.line_received.connect(self._on_build_line)

        tabs = QTabWidget()
        tabs.addTab(self.change_table, "Change Journal")
        tabs.addTab(self.queue_table, "Build Queue")
        tabs.addTab(self.build_output, "Build Output")
        tabs.addTab(self.log_table, "Logs")
        tabs.addTab(self.error_table, "Errors")

        self.main_splitter = QSplitter()
        self.main_splitter.setOrientation(Qt.Orientation.Vertical)
        self.main_splitter.addWidget(top_split)
        self.main_splitter.addWidget(tabs)
        self.main_splitter.setSizes([700, 200])

        root = QWidget()
        layout = QVBoxLayout(root)
        layout.addWidget(self.main_splitter)
        self.setCentralWidget(root)

        status = QStatusBar()
        self.status_label = QLabel("Watcher idle")
        status.addWidget(self.status_label)

        flush_btn = QPushButton("Flush Build Queue")
        flush_btn.clicked.connect(self.flush_queue)
        status.addPermanentWidget(flush_btn)

        play_btn = QPushButton("Play")
        play_btn.clicked.connect(self._launch_game)
        status.addPermanentWidget(play_btn)
        self.setStatusBar(status)

        self._refresh_tree_roots()

    def _refresh_tree_roots(self) -> None:
        source_root = self.settings.source_root().resolve()
        build_root = self.settings.build_root().resolve()
        build_root.mkdir(parents=True, exist_ok=True)
        source_root.mkdir(parents=True, exist_ok=True)

        self.source_model.setRootPath(str(source_root))
        self.source_tree.setRootIndex(self.source_model.index(str(source_root)))
        self.source_tree.configure_root(source_root)
        self.build_model.setRootPath(str(build_root))
        self._refresh_pak_tree(force=True)

    def _selected_source_path(self) -> Path:
        index = self.source_tree.currentIndex()
        if index.isValid():
            return Path(self.source_model.filePath(index))
        return self.settings.source_root().resolve()

    def _target_directory_for_selection(self) -> Path:
        selected = self._selected_source_path()
        return selected if selected.is_dir() else selected.parent

    def _create_source_entry(self) -> None:
        target_dir = self._target_directory_for_selection()
        name, ok = QInputDialog.getText(self, "Neu", "Name für neue Datei/Ordner:")
        if not ok or not name.strip():
            return

        candidate = target_dir / name.strip()
        if candidate.exists():
            QMessageBox.warning(self, "Neu", "Eintrag existiert bereits.")
            return

        try:
            if "." in candidate.name:
                candidate.parent.mkdir(parents=True, exist_ok=True)
                candidate.touch()
            else:
                candidate.mkdir(parents=True, exist_ok=False)
        except OSError as exc:
            QMessageBox.warning(self, "Neu", f"Konnte Eintrag nicht erstellen:\n{exc}")

    def _rename_source_entry(self) -> None:
        selected = self._selected_source_path()
        if selected == self.settings.source_root().resolve():
            QMessageBox.information(self, "Edit", "Der Source-Root kann nicht umbenannt werden.")
            return

        new_name, ok = QInputDialog.getText(self, "Edit", "Neuer Name:", text=selected.name)
        if not ok or not new_name.strip() or new_name.strip() == selected.name:
            return

        target = selected.parent / new_name.strip()
        if target.exists():
            QMessageBox.warning(self, "Edit", "Zielname existiert bereits.")
            return

        try:
            selected.rename(target)
        except OSError as exc:
            QMessageBox.warning(self, "Edit", f"Konnte Eintrag nicht umbenennen:\n{exc}")

    def _delete_source_entry(self) -> None:
        selected = self._selected_source_path()
        if selected == self.settings.source_root().resolve():
            QMessageBox.information(self, "Löschen", "Der Source-Root kann nicht gelöscht werden.")
            return

        confirm = QMessageBox.question(self, "Löschen", f"{selected.name} wirklich löschen?")
        if confirm != QMessageBox.StandardButton.Yes:
            return

        try:
            if selected.is_dir():
                shutil.rmtree(selected)
            else:
                selected.unlink()
        except OSError as exc:
            QMessageBox.warning(self, "Löschen", f"Konnte Eintrag nicht löschen:\n{exc}")

    def _build_menu(self) -> None:
        menu = self.menuBar().addMenu("Project")
        template_action = menu.addAction("New Project from Template...")
        template_action.triggered.connect(self._new_from_template)
        menu.addSeparator()
        settings_action = menu.addAction("Settings")
        settings_action.triggered.connect(self.open_settings)

        build_menu = self.menuBar().addMenu("Build")
        flush_action = build_menu.addAction("Flush Queue")
        flush_action.triggered.connect(self.flush_queue)
        rebuild_action = build_menu.addAction("Rebuild All")
        rebuild_action.triggered.connect(self._rebuild_all)
        clean_action = build_menu.addAction("Clean Build Directory")
        clean_action.triggered.connect(self._clean_build)
        build_menu.addSeparator()
        play_action = build_menu.addAction("Play")
        play_action.triggered.connect(self._launch_game)
        build_menu.addSeparator()
        clear_output_action = build_menu.addAction("Clear Build Output")
        clear_output_action.triggered.connect(self.build_output.clear)

    def _init_timer(self) -> None:
        self.refresh_timer = QTimer(self)
        self.refresh_timer.timeout.connect(self.refresh_tables)
        self.refresh_timer.start(1200)

        self.flush_timer = QTimer(self)
        self.flush_timer.timeout.connect(self._auto_flush)
        minutes = int(self.settings.get("flush_interval_minutes", "3"))
        self.flush_timer.start(minutes * 60 * 1000)

    def _set_preview_widget(self, widget: QWidget) -> None:
        while self.preview_body_layout.count():
            item = self.preview_body_layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        self.preview_body_layout.addWidget(widget)

    def _source_clicked(self, index) -> None:
        path = Path(self.source_model.filePath(index))
        self._update_preview_context(path, "Source")
        if path.is_file():
            handler = self.preview.handler_for(path)
            preview_widget = handler.create_widget(path)

            # Auto-validate certain file types
            diags = None
            suffix = path.suffix.lower()
            if suffix == ".shader":
                diags = self.validation.validate_shader_file(path)
            elif suffix == ".map":
                diags = self.validation.validate_map_entities(path)

            if diags:
                self._set_preview_widget(
                    self._wrap_with_validation(preview_widget, diags)
                )
            else:
                self._set_preview_widget(preview_widget)

    def _wrap_with_validation(
        self, preview_widget: QWidget, diags: list
    ) -> QWidget:
        """Wrap a preview widget with a validation results table below it."""
        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(preview_widget, stretch=3)
        validation_label = QLabel(f"Validation: {len(diags)} issue(s) found")
        validation_label.setStyleSheet("color: orange; font-weight: bold;")
        layout.addWidget(validation_label)
        val_table = QTableWidget(len(diags), 3)
        val_table.setHorizontalHeaderLabels(["Line", "Severity", "Message"])
        for i, d in enumerate(diags):
            val_table.setItem(i, 0, QTableWidgetItem(str(d.line)))
            val_table.setItem(i, 1, QTableWidgetItem(d.severity))
            val_table.setItem(i, 2, QTableWidgetItem(d.message))
        layout.addWidget(val_table, stretch=1)
        return container

    def _refresh_pak_tree(self, force: bool = False) -> None:
        pak_path = self.settings.pak_output_path().resolve()
        pak_exists = pak_path.exists() and pak_path.is_file()
        stat = pak_path.stat() if pak_exists else None
        signature = (pak_exists, int(stat.st_mtime_ns) if stat else 0, stat.st_size if stat else 0)
        if not force and signature == self._last_pak_signature:
            return

        self._last_pak_signature = signature
        self._pak_tree_model.clear()
        self._pak_tree_model.setHorizontalHeaderLabels(["Name", "Size", "Type", "Date Modified"])
        root = self._pak_tree_model.invisibleRootItem()

        pak_root_item = QStandardItem(pak_path.name)
        size_item = QStandardItem(str(stat.st_size) if stat else "")
        pak_type_item = QStandardItem("PAK file" if pak_exists else "Missing PAK")
        date_item = QStandardItem("" if not stat else str(int(stat.st_mtime)))
        root.appendRow([pak_root_item, size_item, pak_type_item, date_item])

        if pak_exists:
            try:
                entries = self.pak_archive.read_entries(pak_path)
            except PakError as exc:
                QMessageBox.warning(self, "PAK", f"Could not read PAK file:\n{exc}")
                pak_root_item.appendRow([QStandardItem("<read error>"), QStandardItem(""), QStandardItem("Error"), QStandardItem("")])
            else:
                self._append_pak_tree(pak_root_item, build_pak_tree([(entry.name, entry.size) for entry in entries]))
                self.build_tree.expandAll()
        else:
            pak_root_item.appendRow([QStandardItem("<not found>"), QStandardItem(""), QStandardItem("Info"), QStandardItem("")])

        self.build_tree_title.setText(f"PAK Content: {pak_path.name}")

    def _append_pak_tree(self, parent: QStandardItem, node: dict[str, dict]) -> None:
        for name in sorted(node.keys()):
            info = node[name]
            if "_children" in info:
                folder_item = QStandardItem(name)
                folder_type = QStandardItem("File Folder")
                parent.appendRow([folder_item, QStandardItem(""), folder_type, QStandardItem("")])
                self._append_pak_tree(folder_item, info["_children"])
                continue

            size = info.get("_size", 0)
            parent.appendRow(
                [
                    QStandardItem(name),
                    QStandardItem(str(size)),
                    QStandardItem("PAK Entry"),
                    QStandardItem(""),
                ]
            )

    def _update_preview_context(self, path: Path, pane_name: str) -> None:
        item_type = "Folder" if path.is_dir() else ("PAK file" if path.suffix.lower() == ".pak" else "File")
        self.preview_context.setText(f"Window: {pane_name} | Item: {item_type} | Path: {path.name}")

    def _new_from_template(self) -> None:
        templates = self.templates.available_templates()
        name, ok = QInputDialog.getItem(
            self, "New Project from Template", "Select template:", templates, 0, False
        )
        if not ok or not name:
            return
        target = self.settings.source_root().resolve().parent
        confirm = QMessageBox.question(
            self, "New Project",
            f"Create '{name}' template in {target}?\nExisting files will not be overwritten.",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        created = self.templates.create_from_template(name, target)
        self._refresh_tree_roots()
        QMessageBox.information(self, "Template", f"Created {len(created)} file(s).")

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            self._refresh_tree_roots()

    def refresh_tables(self) -> None:
        self._fill_table(self.change_table, self.change_journal.latest())
        self._fill_table(self.queue_table, self.build_queue.latest())
        logs = self.logs.latest()
        self._fill_table(self.log_table, logs)
        self._fill_diagnostics_table()
        self._refresh_pak_tree()

    def _fill_table(self, table: QTableWidget, rows: list[tuple]) -> None:
        table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                table.setItem(i, j, QTableWidgetItem(str(val)))

    def _fill_diagnostics_table(self) -> None:
        diags = self._diagnostics
        self.error_table.setRowCount(len(diags))
        for i, d in enumerate(diags):
            self.error_table.setItem(i, 0, QTableWidgetItem(d.file_path))
            self.error_table.setItem(i, 1, QTableWidgetItem(str(d.line)))
            self.error_table.setItem(i, 2, QTableWidgetItem(d.severity))
            self.error_table.setItem(i, 3, QTableWidgetItem(d.message))

    def _error_double_clicked(self, row: int, _col: int) -> None:
        if row >= len(self._diagnostics):
            return
        diag = self._diagnostics[row]
        source_root = self.settings.source_root().resolve()
        file_path = Path(diag.file_path)
        if not file_path.is_absolute():
            file_path = source_root / file_path
        if not file_path.is_file():
            return
        self._update_preview_context(file_path, "Error")
        handler = self.preview.handler_for(file_path)
        widget = handler.create_widget(file_path)
        self._set_preview_widget(widget)
        # Scroll to the error line if the widget is a text editor
        if hasattr(widget, "document") and callable(widget.document):
            from PySide6.QtGui import QTextCursor
            doc = widget.document()
            block = doc.findBlockByLineNumber(diag.line - 1)
            if block.isValid():
                cursor = QTextCursor(block)
                widget.setTextCursor(cursor)
                widget.centerCursor()

    def _update_diagnostics_from_output(self, output: str) -> None:
        new_diags = parse_diagnostics(output)
        if new_diags:
            self._diagnostics = new_diags
            self._fill_diagnostics_table()

    def _auto_flush(self) -> None:
        if self.settings.get("auto_flush", "1") == "1":
            self.flush_queue()

    def _on_build_line(self, stream: str, text: str) -> None:
        prefix = "ERR" if stream == "stderr" else "   "
        self.build_output.appendPlainText(f"[{prefix}] {text}")

    def _build_line_callback(self, stream: str, text: str) -> None:
        """Thread-safe callback passed to streaming compiler methods."""
        self._line_bridge.line_received.emit(stream, text)

    def _rebuild_all(self) -> None:
        confirm = QMessageBox.question(
            self, "Rebuild All",
            "This will clean the build directory and rebuild everything. Continue?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        self.build_output.clear()
        self.build_output.appendPlainText("=== Rebuild All ===")
        result = self.rebuild.rebuild_all(on_line=self._build_line_callback)
        self.build_output.appendPlainText(f"\n{result.summary()}")
        if not result.ok:
            QMessageBox.warning(self, "Rebuild", "Rebuild completed with errors. See Build Output.")

    def _clean_build(self) -> None:
        confirm = QMessageBox.question(
            self, "Clean Build",
            "This will delete all files in the build directory. Continue?",
        )
        if confirm != QMessageBox.StandardButton.Yes:
            return
        ok = self.rebuild.clean_build_dir()
        if ok:
            self.build_output.appendPlainText("[INFO] Build directory cleaned.")
        else:
            QMessageBox.warning(self, "Clean", "Failed to clean build directory. See Logs.")

    def _launch_game(self) -> None:
        exe = self.settings.get("engine_exe", "")
        if not exe:
            QMessageBox.warning(self, "Play", "No engine executable configured. Set it in Settings.")
            return
        proc = self.launch.launch_game()
        if proc is None:
            QMessageBox.warning(self, "Play", "Failed to launch engine. See Logs tab.")

    def flush_queue(self) -> None:
        has_error = False
        while True:
            action = self.build_queue.pop_pending()
            if not action:
                break
            ok = self._execute_action(action)
            if ok:
                self.build_queue.mark_done(action)
            else:
                has_error = True
                self.build_queue.mark_failed(action, "Failed")

        if has_error:
            QMessageBox.warning(self, "Build", "Some build actions failed. See Errors tab.")

    def _execute_action(self, action: BuildAction) -> bool:
        path = self.settings.source_root() / action.relative_path
        if action.action_type == "compile_qc":
            result = self.compiler.compile_qc_streaming(
                self.settings.source_root(), on_line=self._build_line_callback
            )
            if result is not None:
                combined = f"{result.stdout}\n{result.stderr}"
                self._update_diagnostics_from_output(combined)
                return result.code == 0
            return False
        if action.action_type == "compile_map":
            result = self.compiler.compile_map_streaming(
                path, on_line=self._build_line_callback
            )
            if result is not None:
                combined = f"{result.stdout}\n{result.stderr}"
                self._update_diagnostics_from_output(combined)
                return result.code == 0
            return False
        if action.action_type == "rebuild_pak":
            ok = self.pack.rebuild_pak()
            if ok and self.settings.get("deploy_after_build", "0") == "1":
                self.deploy.deploy_pak()
            return ok
        return True
