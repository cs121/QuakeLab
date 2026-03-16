from __future__ import annotations

from pathlib import Path

from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QFileDialog,
    QFormLayout,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QSpinBox,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from core.services.settings_service import SettingsService
from core.services.toolchain_check_service import ToolchainCheckService


class SettingsDialog(QDialog):
    def __init__(self, settings: SettingsService, parent=None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._toolchain_checker = ToolchainCheckService(settings)
        self.setWindowTitle("QuakeLab Settings")
        self.resize(800, 500)

        tabs = QTabWidget()
        tabs.addTab(self._project_tab(), "Project")
        tabs.addTab(self._toolchain_tab(), "Toolchains")
        tabs.addTab(self._build_tab(), "Build")

        save = QPushButton("Save")
        save.clicked.connect(self._save)
        reset_btn = QPushButton("Reset / Clean")
        reset_btn.clicked.connect(self._reset_clean)
        export_btn = QPushButton("Export JSON")
        export_btn.clicked.connect(self._export)
        import_btn = QPushButton("Import JSON")
        import_btn.clicked.connect(self._import)

        row = QHBoxLayout()
        row.addWidget(import_btn)
        row.addWidget(export_btn)
        row.addWidget(reset_btn)
        row.addStretch(1)
        row.addWidget(save)

        layout = QVBoxLayout(self)
        layout.addWidget(tabs)
        layout.addLayout(row)

    def _with_browse_button(self, edit: QLineEdit, title: str, *, directory: bool = False) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(edit)
        browse = QPushButton("Browse…")
        if directory:
            browse.clicked.connect(lambda: self._select_directory(edit, title))
        else:
            browse.clicked.connect(lambda: self._select_file(edit, title))
        layout.addWidget(browse)
        return row

    def _select_directory(self, edit: QLineEdit, title: str) -> None:
        selected = QFileDialog.getExistingDirectory(self, title, edit.text() or str(Path.cwd()))
        if selected:
            edit.setText(selected)

    def _select_file(self, edit: QLineEdit, title: str) -> None:
        selected, _ = QFileDialog.getOpenFileName(self, title, edit.text() or str(Path.cwd()))
        if selected:
            edit.setText(selected)

    def _project_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.source_root = QLineEdit(self.settings.get("source_root", "src"))
        self.build_root = QLineEdit(self.settings.get("build_root", "build"))
        self.deploy_root = QLineEdit(self.settings.get("deploy_root", "deploy"))
        self.pak_output = QLineEdit(self.settings.get("pak_output_path", "build/pak0.pak"))
        self.engine_exe = QLineEdit(self.settings.get("engine_exe", ""))
        form.addRow("Source Root", self._with_browse_button(self.source_root, "Select Source Root", directory=True))
        form.addRow("Build Root", self._with_browse_button(self.build_root, "Select Build Root", directory=True))
        form.addRow("Deploy Root", self._with_browse_button(self.deploy_root, "Select Deploy Root", directory=True))
        form.addRow("Pak Output", self._with_browse_button(self.pak_output, "Select Pak Output File"))
        form.addRow("Engine EXE", self._with_browse_button(self.engine_exe, "Select Game Executable"))
        return w

    def _with_status_indicator(self, edit: QLineEdit, title: str, settings_key: str, label: str) -> QWidget:
        row = QWidget()
        layout = QHBoxLayout(row)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(edit)
        browse = QPushButton("Browse...")
        browse.clicked.connect(lambda: self._select_file(edit, title))
        layout.addWidget(browse)
        indicator = QLabel()
        indicator.setFixedWidth(20)
        layout.addWidget(indicator)
        self._tool_indicators.append((edit, settings_key, label, indicator))
        # Update indicator when text changes
        edit.textChanged.connect(lambda: self._refresh_tool_indicator(settings_key, label, indicator, edit.text()))
        return row

    def _refresh_tool_indicator(self, key: str, label: str, indicator: QLabel, path: str) -> None:
        # Temporarily set the value to check it
        old = self.settings.get(key, "")
        self.settings.set(key, path)
        status = self._toolchain_checker.check_tool(key, label)
        self.settings.set(key, old)
        if not path:
            indicator.setText("")
            indicator.setToolTip("Not configured")
        elif status.ok:
            indicator.setStyleSheet("color: green; font-weight: bold;")
            indicator.setText("OK")
            indicator.setToolTip(f"Found: {status.path}")
        else:
            indicator.setStyleSheet("color: red; font-weight: bold;")
            indicator.setText("X")
            indicator.setToolTip(f"Not found or not executable: {path}")

    def _toolchain_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self._tool_indicators: list[tuple[QLineEdit, str, str, QLabel]] = []
        self.qc_exe = QLineEdit(self.settings.get("qc_executable", ""))
        self.qc_args = QLineEdit(self.settings.get("qc_args", ""))
        self.qbsp_exe = QLineEdit(self.settings.get("qbsp_executable", ""))
        self.vis_exe = QLineEdit(self.settings.get("vis_executable", ""))
        self.light_exe = QLineEdit(self.settings.get("light_executable", ""))
        form.addRow("QC Compiler", self._with_status_indicator(self.qc_exe, "Select QC Compiler", "qc_executable", "QC Compiler"))
        form.addRow("QC Args", self.qc_args)
        form.addRow("QBSP", self._with_status_indicator(self.qbsp_exe, "Select QBSP Executable", "qbsp_executable", "QBSP"))
        form.addRow("VIS", self._with_status_indicator(self.vis_exe, "Select VIS Executable", "vis_executable", "VIS"))
        form.addRow("LIGHT", self._with_status_indicator(self.light_exe, "Select LIGHT Executable", "light_executable", "LIGHT"))
        return w

    def _build_tab(self) -> QWidget:
        w = QWidget()
        form = QFormLayout(w)
        self.auto_watch = QCheckBox()
        self.auto_watch.setChecked(self.settings.get("auto_watch", "1") == "1")
        self.auto_flush = QCheckBox()
        self.auto_flush.setChecked(self.settings.get("auto_flush", "1") == "1")
        self.flush_minutes = QSpinBox()
        self.flush_minutes.setRange(1, 60)
        self.flush_minutes.setValue(int(self.settings.get("flush_interval_minutes", "3")))
        self.pack_after_build = QCheckBox()
        self.pack_after_build.setChecked(self.settings.get("pack_after_build", "1") == "1")
        self.deploy_after_build = QCheckBox()
        self.deploy_after_build.setChecked(self.settings.get("deploy_after_build", "0") == "1")
        self.map_mode = QComboBox()
        self.map_mode.addItems(["fast", "full", "manual"])
        self.map_mode.setCurrentText(self.settings.get("map_build_mode", "fast"))

        form.addRow("Auto Watch", self.auto_watch)
        form.addRow("Auto Flush", self.auto_flush)
        form.addRow("Flush Interval (minutes)", self.flush_minutes)
        form.addRow("Pack after build", self.pack_after_build)
        form.addRow("Deploy after build", self.deploy_after_build)
        form.addRow("Map Build Mode", self.map_mode)
        return w

    def _save(self) -> None:
        self.settings.set("source_root", self.source_root.text())
        self.settings.set("build_root", self.build_root.text())
        self.settings.set("deploy_root", self.deploy_root.text())
        self.settings.set("pak_output_path", self.pak_output.text())
        self.settings.set("engine_exe", self.engine_exe.text())

        self.settings.set("qc_executable", self.qc_exe.text())
        self.settings.set("qc_args", self.qc_args.text())
        self.settings.set("qbsp_executable", self.qbsp_exe.text())
        self.settings.set("vis_executable", self.vis_exe.text())
        self.settings.set("light_executable", self.light_exe.text())

        self.settings.set("auto_watch", "1" if self.auto_watch.isChecked() else "0")
        self.settings.set("auto_flush", "1" if self.auto_flush.isChecked() else "0")
        self.settings.set("flush_interval_minutes", str(self.flush_minutes.value()))
        self.settings.set("pack_after_build", "1" if self.pack_after_build.isChecked() else "0")
        self.settings.set("deploy_after_build", "1" if self.deploy_after_build.isChecked() else "0")
        self.settings.set("map_build_mode", self.map_mode.currentText())
        self.accept()

    def _reset_clean(self) -> None:
        answer = QMessageBox.question(
            self,
            "Reset / Clean",
            "This will rebuild the database, reset all settings and paths to defaults, "
            "and remove project src/build/deploy folders. Continue?",
        )
        if answer != QMessageBox.StandardButton.Yes:
            return

        self.settings.reset_workspace()
        QMessageBox.information(self, "Reset complete", "Workspace has been reset to a clean state.")
        self.accept()

    def _export(self) -> None:
        path, _ = QFileDialog.getSaveFileName(self, "Export Settings", "quakelab-settings.json", "JSON (*.json)")
        if path:
            self.settings.export_json(Path(path))

    def _import(self) -> None:
        path, _ = QFileDialog.getOpenFileName(self, "Import Settings", "", "JSON (*.json)")
        if path:
            self.settings.import_json(Path(path))
