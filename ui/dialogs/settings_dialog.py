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

from core.services.build_profile_service import BuildProfileService
from core.services.settings_service import SettingsService
from core.services.toolchain_check_service import ToolchainCheckService


class SettingsDialog(QDialog):
    def __init__(self, settings: SettingsService, parent=None, build_profile_service: BuildProfileService | None = None) -> None:
        super().__init__(parent)
        self.settings = settings
        self._toolchain_checker = ToolchainCheckService(settings)
        self._profile_service = build_profile_service
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
        self.engine_args_edit = QLineEdit(self.settings.get("engine_args", ""))
        self.entity_def_path = QLineEdit(self.settings.get("entity_def_path", ""))
        form.addRow("Source Root", self._with_browse_button(self.source_root, "Select Source Root", directory=True))
        form.addRow("Build Root", self._with_browse_button(self.build_root, "Select Build Root", directory=True))
        form.addRow("Deploy Root", self._with_browse_button(self.deploy_root, "Select Deploy Root", directory=True))
        form.addRow("Pak Output", self._with_browse_button(self.pak_output, "Select Pak Output File"))
        form.addRow("Engine EXE", self._with_browse_button(self.engine_exe, "Select Game Executable"))
        self.engine_args_edit.setPlaceholderText("e.g. -heapsize 256000 -window")
        form.addRow("Engine Args", self.engine_args_edit)
        self.entity_def_path.setPlaceholderText("Path to .def or .fgd file for Entity Browser")
        form.addRow("Entity Definitions", self._with_browse_button(self.entity_def_path, "Select DEF/FGD File"))
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
        layout = QVBoxLayout(w)
        form = QFormLayout()
        self._tool_indicators: list[tuple[QLineEdit, str, str, QLabel]] = []
        self.qc_exe = QLineEdit(self.settings.get("qc_executable", ""))
        self.qc_args = QLineEdit(self.settings.get("qc_args", ""))
        self.qbsp_exe = QLineEdit(self.settings.get("qbsp_executable", ""))
        self.qbsp_args = QLineEdit(self.settings.get("qbsp_args", ""))
        self.vis_exe = QLineEdit(self.settings.get("vis_executable", ""))
        self.vis_args = QLineEdit(self.settings.get("vis_args", ""))
        self.light_exe = QLineEdit(self.settings.get("light_executable", ""))
        self.light_args = QLineEdit(self.settings.get("light_args", ""))
        form.addRow("QC Compiler", self._with_status_indicator(self.qc_exe, "Select QC Compiler", "qc_executable", "QC Compiler"))
        form.addRow("QC Args", self.qc_args)
        form.addRow("QBSP", self._with_status_indicator(self.qbsp_exe, "Select QBSP Executable", "qbsp_executable", "QBSP"))
        self.qbsp_args.setPlaceholderText("e.g. -leak -oldaxis")
        form.addRow("QBSP Args", self.qbsp_args)
        form.addRow("VIS", self._with_status_indicator(self.vis_exe, "Select VIS Executable", "vis_executable", "VIS"))
        self.vis_args.setPlaceholderText("e.g. -fast")
        form.addRow("VIS Args", self.vis_args)
        form.addRow("LIGHT", self._with_status_indicator(self.light_exe, "Select LIGHT Executable", "light_executable", "LIGHT"))
        self.light_args.setPlaceholderText("e.g. -extra -extra4")
        form.addRow("LIGHT Args", self.light_args)
        layout.addLayout(form)

        auto_detect_btn = QPushButton("Auto-Detect All")
        auto_detect_btn.setToolTip("Search PATH and common directories for Quake tools")
        auto_detect_btn.clicked.connect(self._auto_detect_tools)
        layout.addWidget(auto_detect_btn)
        layout.addStretch(1)
        return w

    def _auto_detect_tools(self) -> None:
        found = self._toolchain_checker.auto_detect_tools()
        if not found:
            QMessageBox.information(self, "Auto-Detect", "No tools found on this system.")
            return
        field_map = {
            "qc_executable": self.qc_exe,
            "qbsp_executable": self.qbsp_exe,
            "vis_executable": self.vis_exe,
            "light_executable": self.light_exe,
            "engine_exe": self.engine_exe,
        }
        applied = []
        for key, path in found.items():
            edit = field_map.get(key)
            if edit and not edit.text():
                edit.setText(path)
                applied.append(key)
        if applied:
            QMessageBox.information(
                self, "Auto-Detect", f"Found {len(applied)} tool(s):\n" + "\n".join(applied)
            )
        else:
            QMessageBox.information(self, "Auto-Detect", "All tool fields already populated.")

    def _build_tab(self) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)
        form = QFormLayout()

        # Build profile selector
        if self._profile_service:
            profile_row = QWidget()
            profile_layout = QHBoxLayout(profile_row)
            profile_layout.setContentsMargins(0, 0, 0, 0)
            self._profile_combo = QComboBox()
            self._refresh_profile_combo()
            self._profile_combo.currentTextChanged.connect(self._on_profile_selected)
            profile_layout.addWidget(self._profile_combo)
            save_profile_btn = QPushButton("Save as Profile...")
            save_profile_btn.clicked.connect(self._save_as_profile)
            profile_layout.addWidget(save_profile_btn)
            form.addRow("Build Profile", profile_row)
        else:
            self._profile_combo = None

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
        layout.addLayout(form)
        layout.addStretch(1)
        return w

    def _refresh_profile_combo(self) -> None:
        if not self._profile_combo or not self._profile_service:
            return
        self._profile_combo.blockSignals(True)
        self._profile_combo.clear()
        self._profile_combo.addItem("")  # no profile
        for p in self._profile_service.list_profiles():
            self._profile_combo.addItem(p.name)
        active = self.settings.get("active_build_profile", "")
        idx = self._profile_combo.findText(active)
        if idx >= 0:
            self._profile_combo.setCurrentIndex(idx)
        self._profile_combo.blockSignals(False)

    def _on_profile_selected(self, name: str) -> None:
        if not name or not self._profile_service:
            return
        profile = self._profile_service.get_profile(name)
        if not profile:
            return
        self.qc_args.setText(profile.qc_args)
        self.qbsp_args.setText(profile.qbsp_args)
        self.vis_args.setText(profile.vis_args)
        self.light_args.setText(profile.light_args)
        self.map_mode.setCurrentText(profile.map_build_mode)

    def _save_as_profile(self) -> None:
        if not self._profile_service:
            return
        from PySide6.QtWidgets import QInputDialog
        name, ok = QInputDialog.getText(self, "Save Build Profile", "Profile name:")
        if not ok or not name.strip():
            return
        from core.services.build_profile_service import BuildProfile
        profile = BuildProfile(
            id=0,
            name=name.strip(),
            qc_args=self.qc_args.text(),
            qbsp_args=self.qbsp_args.text(),
            vis_args=self.vis_args.text(),
            light_args=self.light_args.text(),
            map_build_mode=self.map_mode.currentText(),
        )
        self._profile_service.save_profile(profile)
        self._refresh_profile_combo()
        self._profile_combo.setCurrentText(name.strip())

    def _save(self) -> None:
        self.settings.set("source_root", self.source_root.text())
        self.settings.set("build_root", self.build_root.text())
        self.settings.set("deploy_root", self.deploy_root.text())
        self.settings.set("pak_output_path", self.pak_output.text())
        self.settings.set("engine_exe", self.engine_exe.text())
        self.settings.set("engine_args", self.engine_args_edit.text())
        self.settings.set("entity_def_path", self.entity_def_path.text())

        self.settings.set("qc_executable", self.qc_exe.text())
        self.settings.set("qc_args", self.qc_args.text())
        self.settings.set("qbsp_executable", self.qbsp_exe.text())
        self.settings.set("qbsp_args", self.qbsp_args.text())
        self.settings.set("vis_executable", self.vis_exe.text())
        self.settings.set("vis_args", self.vis_args.text())
        self.settings.set("light_executable", self.light_exe.text())
        self.settings.set("light_args", self.light_args.text())

        self.settings.set("auto_watch", "1" if self.auto_watch.isChecked() else "0")
        self.settings.set("auto_flush", "1" if self.auto_flush.isChecked() else "0")
        self.settings.set("flush_interval_minutes", str(self.flush_minutes.value()))
        self.settings.set("pack_after_build", "1" if self.pack_after_build.isChecked() else "0")
        self.settings.set("deploy_after_build", "1" if self.deploy_after_build.isChecked() else "0")
        self.settings.set("map_build_mode", self.map_mode.currentText())
        if self._profile_combo:
            self.settings.set("active_build_profile", self._profile_combo.currentText())
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
