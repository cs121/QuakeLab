from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QTimer, Qt
from PySide6.QtGui import QStandardItem, QStandardItemModel
from PySide6.QtWidgets import (
    QFileSystemModel,
    QFrame,
    QLabel,
    QMainWindow,
    QMenu,
    QMessageBox,
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

from core.models.domain import BuildAction
from core.services.build_queue_service import BuildQueueService
from core.services.change_journal_service import ChangeJournalService
from core.services.compiler_service import CompilerService
from core.services.deploy_service import DeployService
from core.services.log_service import LogService
from core.services.pack_service import PackService
from core.services.preview_service import PreviewService
from core.services.project_service import ProjectService
from core.services.settings_service import SettingsService
from infrastructure.archives.pak import PakArchive, PakError
from infrastructure.filesystem.watcher import PollingWatchService
from ui.dialogs.settings_dialog import SettingsDialog


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
        self.watch = watch_service
        self.preview = preview_service
        self.logs = log_service
        self.pak_archive = PakArchive()
        self._showing_pak_contents = False

        self.setWindowTitle("QuakeLab Workbench V1")
        self.resize(1400, 900)
        self._build_ui()
        self._init_timer()

    def _build_ui(self) -> None:
        self._build_menu()

        self.source_model = QFileSystemModel(self)
        self.source_tree_title = QLabel("Source")
        self.source_tree_title.setToolTip("Displays source assets and editable files")
        self.source_tree = QTreeView()
        self.source_tree.setModel(self.source_model)
        self.source_tree.clicked.connect(self._source_clicked)

        self.build_model = QFileSystemModel(self)
        self.build_tree_title = QLabel("Build / PAK")
        self.build_tree_title.setToolTip("Displays build output, including generated PAK files")
        self.build_tree = QTreeView()
        self.build_tree.setModel(self.build_model)
        self.build_tree.clicked.connect(self._build_clicked)

        source_panel = QWidget()
        source_layout = QVBoxLayout(source_panel)
        source_layout.setContentsMargins(0, 0, 0, 0)
        source_layout.addWidget(self.source_tree_title)
        source_layout.addWidget(self.source_tree)

        build_panel = QWidget()
        build_layout = QVBoxLayout(build_panel)
        build_layout.setContentsMargins(0, 0, 0, 0)
        build_layout.addWidget(self.build_tree_title)
        self.back_to_build_button = QPushButton("Back to Build Folder")
        self.back_to_build_button.clicked.connect(self._show_build_filesystem)
        self.back_to_build_button.setVisible(False)
        build_layout.addWidget(self.back_to_build_button)
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
        self.error_table.setHorizontalHeaderLabels(["Time", "Level", "Source", "Message"])

        tabs = QTabWidget()
        tabs.addTab(self.change_table, "Change Journal")
        tabs.addTab(self.queue_table, "Build Queue")
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
        self.setStatusBar(status)

        self._refresh_tree_roots()

    def _refresh_tree_roots(self) -> None:
        source_root = self.settings.source_root().resolve()
        build_root = self.settings.build_root().resolve()
        build_root.mkdir(parents=True, exist_ok=True)
        source_root.mkdir(parents=True, exist_ok=True)

        self.source_model.setRootPath(str(source_root))
        self.source_tree.setRootIndex(self.source_model.index(str(source_root)))
        self.build_model.setRootPath(str(build_root))
        self.build_tree.setRootIndex(self.build_model.index(str(build_root)))
        self.build_tree.setModel(self.build_model)
        self.build_tree_title.setText("Build / PAK")
        self.back_to_build_button.setVisible(False)
        self._showing_pak_contents = False

    def _build_menu(self) -> None:
        menu = self.menuBar().addMenu("Project")
        settings_action = menu.addAction("Settings")
        settings_action.triggered.connect(self.open_settings)

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
            self._set_preview_widget(handler.create_widget(path))

    def _build_clicked(self, index) -> None:
        if self._showing_pak_contents:
            return
        path = Path(self.build_model.filePath(index))
        self._update_preview_context(path, "Build / PAK")
        if path.is_file():
            if path.suffix.lower() == ".pak":
                self._show_pak_contents(path)
            handler = self.preview.handler_for(path)
            self._set_preview_widget(handler.create_widget(path))

    def _show_build_filesystem(self) -> None:
        self._refresh_tree_roots()

    def _show_pak_contents(self, pak_path: Path) -> None:
        try:
            entries = self.pak_archive.read_entries(pak_path)
        except PakError as exc:
            QMessageBox.warning(self, "PAK", f"Could not read PAK file:\n{exc}")
            return

        tree_model = QStandardItemModel(self)
        tree_model.setHorizontalHeaderLabels(["Name", "Size", "Type", "Date Modified"])
        root = tree_model.invisibleRootItem()
        self._append_pak_tree(root, build_pak_tree([(entry.name, entry.size) for entry in entries]))

        self.build_tree.setModel(tree_model)
        self.build_tree.expandAll()
        self.build_tree_title.setText(f"PAK Content: {pak_path.name}")
        self.back_to_build_button.setVisible(True)
        self._showing_pak_contents = True

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

    def open_settings(self) -> None:
        dialog = SettingsDialog(self.settings, self)
        if dialog.exec():
            self._refresh_tree_roots()

    def refresh_tables(self) -> None:
        self._fill_table(self.change_table, self.change_journal.latest())
        self._fill_table(self.queue_table, self.build_queue.latest())
        logs = self.logs.latest()
        self._fill_table(self.log_table, logs)
        self._fill_table(self.error_table, [log for log in logs if log[1] == "ERROR"])

    def _fill_table(self, table: QTableWidget, rows: list[tuple]) -> None:
        table.setRowCount(len(rows))
        for i, row in enumerate(rows):
            for j, val in enumerate(row):
                table.setItem(i, j, QTableWidgetItem(str(val)))

    def _auto_flush(self) -> None:
        if self.settings.get("auto_flush", "1") == "1":
            self.flush_queue()

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
            return self.compiler.compile_qc(self.settings.source_root())
        if action.action_type == "compile_map":
            return self.compiler.compile_map(path)
        if action.action_type == "rebuild_pak":
            ok = self.pack.rebuild_pak()
            if ok and self.settings.get("deploy_after_build", "0") == "1":
                self.deploy.deploy_pak()
            return ok
        return True
