"""Quake 1 DEM demo file viewer – header info and message statistics."""
from __future__ import annotations

import struct
from pathlib import Path

from PySide6.QtWidgets import (
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from ui.viewers.base import PreviewHandler


def _parse_dem(data: bytes) -> dict:
    """Extract basic statistics from a Quake 1 demo."""
    result: dict = {}
    result["file_size"] = len(data)

    # The demo starts with a null-terminated string for the initial serverinfo message.
    # We try to detect the format by looking for a leading text string.
    if len(data) < 4:
        result["error"] = "File too small"
        return result

    # Quake 1 demo: first 4 bytes are a float (cd track), then message blocks
    # QuakeWorld demo: starts with "QWD\n" or similar text header
    if data[:3] == b"QWD":
        result["format"] = "QuakeWorld Demo"
    elif data[:4] == b"DEMO":
        result["format"] = "Quake Demo (DEMO)"
    else:
        # Try to read as standard Quake demo
        result["format"] = "Quake Demo"

    # Scan message blocks: each is viewangles(3 floats) + length(int32) + data
    pos = 0
    num_messages = 0
    total_bytes = 0
    max_scan = min(len(data), 512 * 1024)  # scan at most 512 KB

    while pos + 16 <= max_scan:
        try:
            # viewangles: 3 floats (12 bytes)
            _yaw, _pitch, _roll = struct.unpack_from("<fff", data, pos)
            pos += 12
            if pos + 4 > len(data):
                break
            msg_len = struct.unpack_from("<I", data, pos)[0]
            pos += 4
            if msg_len > 65536 or pos + msg_len > len(data):
                break
            total_bytes += msg_len
            num_messages += 1
            pos += msg_len
        except struct.error:
            break

    result["messages_scanned"] = num_messages
    result["message_bytes_scanned"] = total_bytes
    result["first_16_bytes"] = data[:16].hex(" ")
    return result


class DemPreviewHandler(PreviewHandler):
    exts = {".dem"}

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in self.exts

    def create_widget(self, path: Path) -> QWidget:
        w = QWidget()
        layout = QVBoxLayout(w)

        try:
            data = path.read_bytes()
        except OSError as exc:
            layout.addWidget(QLabel(f"Cannot read DEM file:\n{exc}"))
            return w

        stats = _parse_dem(data)

        rows = [
            ("File", path.name),
            ("Size", f"{stats['file_size']:,} bytes"),
            ("Format", stats.get("format", "Unknown")),
            ("Messages scanned", str(stats.get("messages_scanned", "N/A"))),
            ("Message data scanned", f"{stats.get('message_bytes_scanned', 0):,} bytes"),
            ("First 16 bytes", stats.get("first_16_bytes", "")),
        ]
        if "error" in stats:
            rows.append(("Error", stats["error"]))

        table = QTableWidget(len(rows), 2)
        table.setHorizontalHeaderLabels(["Property", "Value"])
        for i, (k, v) in enumerate(rows):
            table.setItem(i, 0, QTableWidgetItem(k))
            table.setItem(i, 1, QTableWidgetItem(v))
        table.resizeColumnsToContents()
        layout.addWidget(table)

        note = QLabel(
            "Demo playback is not supported – showing header statistics only."
        )
        note.setStyleSheet("color: gray; font-style: italic;")
        layout.addWidget(note)
        return w
