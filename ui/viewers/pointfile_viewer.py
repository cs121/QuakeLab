from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QLabel, QVBoxLayout, QWidget

from core.parsers.pointfile_parser import parse_pointfile
from ui.viewers.base import PreviewHandler


class _PointfileCanvas(QWidget):
    """2D top-down (XY plane) visualization of a leak path."""

    def __init__(self, points: list[tuple[float, float, float]], parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.points = points
        self.setMinimumSize(200, 200)

    def paintEvent(self, event) -> None:  # noqa: N802
        if len(self.points) < 2:
            return
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        painter.fillRect(self.rect(), QColor(30, 30, 30))

        xs = [p[0] for p in self.points]
        ys = [p[1] for p in self.points]
        min_x, max_x = min(xs), max(xs)
        min_y, max_y = min(ys), max(ys)
        range_x = max_x - min_x or 1.0
        range_y = max_y - min_y or 1.0

        pad = 20
        w = self.width() - 2 * pad
        h = self.height() - 2 * pad
        scale = min(w / range_x, h / range_y)

        def to_screen(x: float, y: float) -> QPointF:
            sx = pad + (x - min_x) * scale
            sy = pad + (max_y - y) * scale  # flip Y
            return QPointF(sx, sy)

        # Draw lines
        pen = QPen(QColor(255, 200, 50), 1.5)
        painter.setPen(pen)
        for i in range(len(self.points) - 1):
            p1 = to_screen(self.points[i][0], self.points[i][1])
            p2 = to_screen(self.points[i + 1][0], self.points[i + 1][1])
            painter.drawLine(p1, p2)

        # Start point (green)
        start = to_screen(self.points[0][0], self.points[0][1])
        painter.setBrush(QColor(0, 200, 0))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(start, 5, 5)

        # End point (red)
        end = to_screen(self.points[-1][0], self.points[-1][1])
        painter.setBrush(QColor(200, 0, 0))
        painter.drawEllipse(end, 5, 5)

        painter.end()


class PointfilePreviewHandler(PreviewHandler):
    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() == ".pts"

    def create_widget(self, path: Path) -> QWidget:
        data = parse_pointfile(path)
        if not data.points:
            return QLabel(f"Pointfile is empty: {path.name}")

        container = QWidget()
        layout = QVBoxLayout(container)
        layout.setContentsMargins(4, 4, 4, 4)

        info = QLabel(f"Leak path: {len(data.points)} points | Start = green, End = red | File: {path.name}")
        info.setStyleSheet("color: orange; font-weight: bold;")
        layout.addWidget(info)

        canvas = _PointfileCanvas(data.points)
        layout.addWidget(canvas, stretch=1)
        return container
