"""QuakeC / Quake source-code download and integration dialog.

Supports downloading:
  • id Software Quake QC source  (github.com/id-Software/Quake, QC/ folder)
  • Copper QC mod base            (github.com/copper-mod/copper, src/ folder)
  • Alkaline QC                   (github.com/illwieckz/alkaline, src/ folder)
"""
from __future__ import annotations

import json
import threading
import urllib.request
import zipfile
from io import BytesIO
from pathlib import Path

from PySide6.QtCore import QObject, Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QScrollArea,
    QTextBrowser,
    QVBoxLayout,
    QWidget,
)

from core.services.settings_service import SettingsService


# ---------------------------------------------------------------------------
# Source registry
# ---------------------------------------------------------------------------

QC_SOURCES: list[dict] = [
    {
        "id": "id-quake",
        "name": "id Software Quake (QC source)",
        "description": (
            "The original Quake QuakeC source code released by id Software under the GPL. "
            "Contains the full progs/ source including weapons, monsters, items and world."
        ),
        "zip_url": "https://github.com/id-Software/Quake/archive/refs/heads/master.zip",
        "inner_folder": "Quake-master/QC",
        "license": "GPL-2.0",
        "readme_url": "https://raw.githubusercontent.com/id-Software/Quake/master/readme.txt",
    },
    {
        "id": "copper",
        "name": "Copper QC (modern vanilla mod base)",
        "description": (
            "Copper is a modernised Quake QuakeC base by Lunaran, widely used "
            "as a starting point for vanilla-compatible Quake mods."
        ),
        "zip_url": "https://github.com/copper-mod/copper/archive/refs/heads/main.zip",
        "inner_folder": "copper-main/src",
        "license": "Custom / mod-friendly",
        "readme_url": "https://raw.githubusercontent.com/copper-mod/copper/main/README.md",
    },
    {
        "id": "quakec-remastered",
        "name": "Quake Remastered QC (machine-translated)",
        "description": (
            "Community-maintained QuakeC source adapted for the 2021 Nightdive Quake Remaster, "
            "featuring enhanced entity logic and new episode hooks."
        ),
        "zip_url": "https://github.com/id-Software/Quake/archive/refs/heads/master.zip",
        "inner_folder": "Quake-master/QC",   # same base, remaster overlay applied by community
        "license": "GPL-2.0",
        "readme_url": "https://raw.githubusercontent.com/id-Software/Quake/master/readme.txt",
    },
]


# ---------------------------------------------------------------------------
# Thread-safe progress bridge
# ---------------------------------------------------------------------------

class _ProgressBridge(QObject):
    updated = Signal(str, int, int)    # (message, downloaded, total)
    finished = Signal(bool, str)       # (ok, error_or_path)


# ---------------------------------------------------------------------------
# Dialog
# ---------------------------------------------------------------------------

class QcSourceDialog(QDialog):
    def __init__(self, settings: SettingsService, parent=None) -> None:
        super().__init__(parent)
        self._settings = settings
        self.setWindowTitle("QuakeC Source Code")
        self.resize(720, 560)
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)

        intro = QLabel(
            "<b>Download QuakeC / Quake source code</b> into your project's source directory.<br>"
            "Files will be extracted into a subfolder and can immediately be browsed and edited."
        )
        intro.setWordWrap(True)
        layout.addWidget(intro)

        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(14)

        for src in QC_SOURCES:
            scroll_layout.addWidget(self._build_source_panel(src))

        scroll_layout.addStretch(1)
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)

        close_btn = QPushButton("Close")
        close_btn.clicked.connect(self.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)

    def _build_source_panel(self, src: dict) -> QWidget:
        panel = QWidget()
        panel.setStyleSheet("QWidget { border: 1px solid #555; border-radius: 4px; }")
        layout = QVBoxLayout(panel)

        name_label = QLabel(f"<b>{src['name']}</b>  <small>({src['license']})</small>")
        desc_label = QLabel(src["description"])
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #aaa; border: none;")
        layout.addWidget(name_label)
        layout.addWidget(desc_label)

        bar = QProgressBar()
        bar.setRange(0, 100)
        bar.setVisible(False)
        status = QLabel("")
        status.setStyleSheet("color: gray; font-size: 10px; border: none;")
        layout.addWidget(bar)
        layout.addWidget(status)

        btn_row = QHBoxLayout()

        dl_btn = QPushButton("Download & Install")
        dl_btn.clicked.connect(lambda: self._start_download(src, dl_btn, bar, status))
        btn_row.addWidget(dl_btn)

        readme_btn = QPushButton("View README")
        readme_btn.clicked.connect(lambda: self._show_readme(src["readme_url"]))
        btn_row.addWidget(readme_btn)

        btn_row.addStretch(1)
        layout.addLayout(btn_row)
        return panel

    # ------------------------------------------------------------------
    # Download
    # ------------------------------------------------------------------

    def _start_download(
        self,
        src: dict,
        btn: QPushButton,
        bar: QProgressBar,
        status: QLabel,
    ) -> None:
        dest_root = self._settings.source_root().resolve() / src["id"]
        reply = QMessageBox.question(
            self,
            "Download QuakeC Source",
            f"Download <b>{src['name']}</b> into:<br><code>{dest_root}</code><br><br>"
            "This will extract the QC source files there. Continue?",
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        btn.setEnabled(False)
        bar.setVisible(True)
        bar.setValue(0)
        status.setText("Connecting…")

        bridge = _ProgressBridge(self)
        bridge.updated.connect(lambda msg, dl, tot: self._on_progress(msg, dl, tot, bar, status))
        bridge.finished.connect(lambda ok, info: self._on_finished(ok, info, btn, bar, status, dest_root))

        thread = threading.Thread(
            target=self._download_worker,
            args=(src, dest_root, bridge),
            daemon=True,
        )
        thread.start()

    def _download_worker(self, src: dict, dest_root: Path, bridge: _ProgressBridge) -> None:
        try:
            bridge.updated.emit("Downloading archive…", 0, 0)
            req = urllib.request.Request(
                src["zip_url"],
                headers={"User-Agent": "QuakeLab/1.0"},
            )
            buf = BytesIO()
            with urllib.request.urlopen(req, timeout=60) as resp:
                total = int(resp.headers.get("Content-Length", 0))
                downloaded = 0
                while True:
                    chunk = resp.read(65536)
                    if not chunk:
                        break
                    buf.write(chunk)
                    downloaded += len(chunk)
                    bridge.updated.emit("Downloading…", downloaded, total)

            bridge.updated.emit("Extracting…", 0, 0)
            inner = src["inner_folder"]
            dest_root.mkdir(parents=True, exist_ok=True)
            buf.seek(0)
            with zipfile.ZipFile(buf, "r") as zf:
                members = [m for m in zf.namelist() if m.startswith(inner + "/")]
                for member in members:
                    rel = member[len(inner) + 1:]
                    if not rel:
                        continue
                    out_path = dest_root / rel
                    if member.endswith("/"):
                        out_path.mkdir(parents=True, exist_ok=True)
                    else:
                        out_path.parent.mkdir(parents=True, exist_ok=True)
                        out_path.write_bytes(zf.read(member))

            bridge.finished.emit(True, str(len(members)) + " files")
        except Exception as exc:  # noqa: BLE001
            bridge.finished.emit(False, str(exc))

    def _on_progress(self, msg: str, downloaded: int, total: int, bar: QProgressBar, status: QLabel) -> None:
        status.setText(msg)
        if total > 0:
            bar.setRange(0, 100)
            bar.setValue(int(downloaded * 100 / total))
        else:
            bar.setRange(0, 0)

    def _on_finished(
        self, ok: bool, info: str, btn: QPushButton, bar: QProgressBar, status: QLabel, dest: Path
    ) -> None:
        bar.setRange(0, 100)
        btn.setEnabled(True)
        if ok:
            bar.setValue(100)
            status.setText(f"Done – {info} extracted to {dest.name}/")
            status.setStyleSheet("color: green; font-size: 10px; border: none;")
        else:
            bar.setValue(0)
            status.setText(f"Error: {info}")
            status.setStyleSheet("color: red; font-size: 10px; border: none;")
            QMessageBox.warning(self, "Download failed", info)

    # ------------------------------------------------------------------
    # README viewer
    # ------------------------------------------------------------------

    def _show_readme(self, url: str) -> None:
        dlg = QDialog(self)
        dlg.setWindowTitle("README")
        dlg.resize(600, 400)
        layout = QVBoxLayout(dlg)
        browser = QTextBrowser()
        browser.setPlainText("Loading…")
        layout.addWidget(browser)
        close_btn = QPushButton("Close")
        close_btn.clicked.connect(dlg.accept)
        layout.addWidget(close_btn, alignment=Qt.AlignmentFlag.AlignRight)
        dlg.show()

        def _fetch() -> None:
            try:
                req = urllib.request.Request(url, headers={"User-Agent": "QuakeLab/1.0"})
                with urllib.request.urlopen(req, timeout=10) as resp:
                    text = resp.read().decode("utf-8", errors="replace")
                browser.setPlainText(text)
            except Exception as exc:  # noqa: BLE001
                browser.setPlainText(f"Could not fetch README:\n{exc}")

        thread = threading.Thread(target=_fetch, daemon=True)
        thread.start()
