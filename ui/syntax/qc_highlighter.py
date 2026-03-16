from __future__ import annotations

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat


class QcHighlighter(QSyntaxHighlighter):
    def __init__(self, parent) -> None:
        super().__init__(parent)

        keyword_fmt = QTextCharFormat()
        keyword_fmt.setForeground(QColor("#569CD6"))
        keyword_fmt.setFontWeight(700)

        builtin_fmt = QTextCharFormat()
        builtin_fmt.setForeground(QColor("#DCDCAA"))

        type_fmt = QTextCharFormat()
        type_fmt.setForeground(QColor("#4EC9B0"))

        string_fmt = QTextCharFormat()
        string_fmt.setForeground(QColor("#CE9178"))

        comment_fmt = QTextCharFormat()
        comment_fmt.setForeground(QColor("#6A9955"))

        number_fmt = QTextCharFormat()
        number_fmt.setForeground(QColor("#B5CEA8"))

        preproc_fmt = QTextCharFormat()
        preproc_fmt.setForeground(QColor("#C586C0"))

        constant_fmt = QTextCharFormat()
        constant_fmt.setForeground(QColor("#4FC1FF"))

        self.rules = [
            # Keywords
            (QRegularExpression(
                r"\b(if|else|while|do|for|return|local|self|other|world"
                r"|break|continue|switch|case|default)\b"
            ), keyword_fmt),
            # Types
            (QRegularExpression(
                r"\b(void|float|vector|string|entity)\b"
            ), type_fmt),
            # Built-in functions
            (QRegularExpression(
                r"\b(spawn|remove|find|findradius|nextent|precache_model|precache_sound"
                r"|precache_file|makevectors|setorigin|setmodel|setsize"
                r"|sprint|bprint|dprint|ftos|vtos|objerror|error"
                r"|WriteByte|WriteChar|WriteShort|WriteLong|WriteCoord|WriteAngle|WriteString|WriteEntity"
                r"|random|rint|floor|ceil|fabs|normalize|vlen|vectoangles|vectoforward"
                r"|changelevel|localsound|stuffcmd|particle|lightstyle"
                r"|cvar|cvar_set|centerprint|ambientsound|traceline"
                r"|droptofloor|walkmove|movetogoal|aim|sound|pointcontents"
                r"|checkbottom|checkpos)\b"
            ), builtin_fmt),
            # Constants (common Quake QC defines)
            (QRegularExpression(
                r"\b(TRUE|FALSE|MOVETYPE_\w+|SOLID_\w+|FL_\w+|EF_\w+|IT_\w+|CHAN_\w+|ATTN_\w+|CONTENT_\w+)\b"
            ), constant_fmt),
            # Numbers
            (QRegularExpression(r"\b\d+\.?\d*\b"), number_fmt),
            # Strings
            (QRegularExpression(r'"[^"]*"'), string_fmt),
            # Preprocessor
            (QRegularExpression(r"^\s*#\w+.*$"), preproc_fmt),
            # Single-line comments
            (QRegularExpression(r"//[^\n]*"), comment_fmt),
        ]

        # Multi-line comment state
        self._comment_fmt = comment_fmt
        self._comment_start = QRegularExpression(r"/\*")
        self._comment_end = QRegularExpression(r"\*/")

    def highlightBlock(self, text: str) -> None:
        # Apply single-line rules
        for rx, fmt in self.rules:
            it = rx.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)

        # Multi-line comment handling
        self.setCurrentBlockState(0)
        start_index = 0

        if self.previousBlockState() != 1:
            match = self._comment_start.match(text)
            start_index = match.capturedStart() if match.hasMatch() else -1
        else:
            start_index = 0

        while start_index >= 0:
            end_match = self._comment_end.match(text, start_index + 2)
            if end_match.hasMatch():
                length = end_match.capturedEnd() - start_index
                self.setFormat(start_index, length, self._comment_fmt)
                next_match = self._comment_start.match(text, end_match.capturedEnd())
                start_index = next_match.capturedStart() if next_match.hasMatch() else -1
            else:
                self.setCurrentBlockState(1)
                self.setFormat(start_index, len(text) - start_index, self._comment_fmt)
                break
