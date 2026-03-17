from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, QTimer, Signal, QObject
from PySide6.QtWidgets import (
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
    QWidget,
)

from core.services.tool_download_service import DownloadProgress, ToolDownloadService


class _ProgressBridge(QObject):
    """Thread-safe bridge: emits Qt signal when download progress updates."""
    updated = Signal(object)  # DownloadProgress


class ToolDownloadDialog(QDialog):
    """Dialog for automatically downloading and installing Quake tools."""

    def __init__(self, service: ToolDownloadService, parent=None) -> None:
        super().__init__(parent)
        self._service = service
        self._bridges: dict[str, _ProgressBridge] = {}
        self._progress_labels: dict[str, QLabel] = {}
        self._progress_bars: dict[str, QProgressBar] = {}
        self._download_btns: dict[str, QPushButton] = {}

        self.setWindowTitle("Download Tools")
        self.resize(600, 400)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        intro = QLabel(
            "Download and install Quake tools automatically.\n"
            "Tools are installed to the <b>toolchain/</b> folder and settings are configured automatically."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(12)

        for tool_name in self._service.available_tools():
            panel = self._build_tool_panel(tool_name)
            scroll_layout.addWidget(panel)

        scroll_layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        toolchain_info = QLabel(f"Toolchain directory: {self._service.toolchain_dir()}")
        toolchain_info.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(toolchain_info)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _build_tool_panel(self, tool_name: str) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(8, 8, 8, 8)
        panel.setStyleSheet("QWidget { border: 1px solid #ccc; border-radius: 4px; }")

        header = QHBoxLayout()
        name_label = QLabel(f"<b>{tool_name}</b>")
        desc_label = QLabel(self._service.tool_description(tool_name))
        desc_label.setStyleSheet("color: gray;")
        header.addWidget(name_label)
        header.addWidget(desc_label, stretch=1)
        layout.addLayout(header)

        progress_bar = QProgressBar()
        progress_bar.setRange(0, 100)
        progress_bar.setVisible(False)
        self._progress_bars[tool_name] = progress_bar
        layout.addWidget(progress_bar)

        status_label = QLabel("")
        status_label.setStyleSheet("color: gray; font-size: 10px;")
        self._progress_labels[tool_name] = status_label
        layout.addWidget(status_label)

        btn_row = QHBoxLayout()

        dl_btn = QPushButton("Download & Install")
        dl_btn.clicked.connect(lambda: self._start_download(tool_name))
        self._download_btns[tool_name] = dl_btn
        btn_row.addWidget(dl_btn)

        local_btn = QPushButton("Install from Archive…")
        local_btn.clicked.connect(lambda: self._install_from_local(tool_name))
        btn_row.addWidget(local_btn)

        btn_row.addStretch(1)
        layout.addLayout(btn_row)
        return panel

    def _start_download(self, tool_name: str) -> None:
        btn = self._download_btns[tool_name]
        btn.setEnabled(False)
        bar = self._progress_bars[tool_name]
        bar.setVisible(True)
        bar.setValue(0)
        label = self._progress_labels[tool_name]
        label.setText("Starting download…")
        label.setStyleSheet("color: blue; font-size: 10px;")

        bridge = _ProgressBridge()
        self._bridges[tool_name] = bridge
        bridge.updated.connect(lambda prog: self._on_progress(tool_name, prog))

        self._service.download_async(
            tool_name,
            on_progress=bridge.updated.emit,
            auto_configure=True,
        )

    def _on_progress(self, tool_name: str, prog: DownloadProgress) -> None:
        bar = self._progress_bars[tool_name]
        label = self._progress_labels[tool_name]

        if prog.total > 0:
            pct = int(prog.downloaded * 100 / prog.total)
            bar.setValue(pct)
        elif prog.downloaded > 0:
            bar.setRange(0, 0)  # indeterminate

        label.setText(prog.message)

        if prog.done:
            bar.setRange(0, 100)
            if prog.ok:
                bar.setValue(100)
                label.setText(f"Installed: {', '.join(prog.installed_paths.keys())}")
                label.setStyleSheet("color: green; font-size: 10px;")
                QMessageBox.information(
                    self,
                    "Download Complete",
                    f"{tool_name} installed successfully.\n"
                    f"Settings have been updated automatically.",
                )
            else:
                bar.setValue(0)
                label.setText(f"Error: {prog.error}")
                label.setStyleSheet("color: red; font-size: 10px;")
                QMessageBox.warning(self, "Download Failed", f"Failed to download {tool_name}:\n{prog.error}")
            btn = self._download_btns[tool_name]
            btn.setEnabled(True)

    def _install_from_local(self, tool_name: str) -> None:
        path_str, _ = QFileDialog.getOpenFileName(
            self,
            f"Select archive for {tool_name}",
            str(Path.home()),
            "Archives (*.zip *.tar.gz *.tgz *.tar.bz2 *.tar.xz);;All files (*)",
        )
        if not path_str:
            return

        label = self._progress_labels[tool_name]
        label.setText("Installing…")
        label.setStyleSheet("color: blue; font-size: 10px;")

        try:
            installed = self._service.install_from_archive(tool_name, Path(path_str), auto_configure=True)
            if installed:
                label.setText(f"Installed: {', '.join(installed.keys())}")
                label.setStyleSheet("color: green; font-size: 10px;")
                QMessageBox.information(
                    self,
                    "Install Complete",
                    f"{tool_name} installed successfully.\n"
                    f"Settings have been updated automatically.",
                )
            else:
                label.setText("No executables found in archive.")
                label.setStyleSheet("color: orange; font-size: 10px;")
        except Exception as exc:  # noqa: BLE001
            label.setText(f"Error: {exc}")
            label.setStyleSheet("color: red; font-size: 10px;")
            QMessageBox.warning(self, "Install Failed", f"Failed to install {tool_name}:\n{exc}")
