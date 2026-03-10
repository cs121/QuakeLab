from __future__ import annotations

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat


class GlslHighlighter(QSyntaxHighlighter):
    def __init__(self, parent) -> None:
        super().__init__(parent)
        keyword = QTextCharFormat()
        keyword.setForeground(QColor("#569CD6"))
        keyword.setFontWeight(700)
        self.rules = [
            (QRegularExpression(r"\\b(void|vec[234]|mat[234]|uniform|in|out|if|else|for|while|return|float|int)\\b"), keyword)
        ]

    def highlightBlock(self, text: str) -> None:
        for rx, fmt in self.rules:
            it = rx.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)
