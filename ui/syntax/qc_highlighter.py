"""QuakeC syntax highlighter for PySide6 QPlainTextEdit / QTextEdit."""
from __future__ import annotations

from PySide6.QtCore import QRegularExpression
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat


def _fmt(color: str, bold: bool = False, italic: bool = False) -> QTextCharFormat:
    f = QTextCharFormat()
    f.setForeground(QColor(color))
    if bold:
        f.setFontWeight(QFont.Weight.Bold)
    if italic:
        f.setFontItalic(True)
    return f


class QcHighlighter(QSyntaxHighlighter):
    """Syntax highlighter for QuakeC (.qc) source files."""

    def __init__(self, parent) -> None:
        super().__init__(parent)

        kw_type = _fmt("#4EC9B0", bold=True)       # teal – types
        kw_flow = _fmt("#C586C0", bold=True)       # purple – control flow
        kw_special = _fmt("#DCDCAA", bold=True)    # yellow – special keywords
        builtin = _fmt("#9CDCFE")                   # light blue – builtins
        field_color = _fmt("#CE9178")               # orange – field declarations
        number = _fmt("#B5CEA8")                    # green – numbers
        string = _fmt("#CE9178")                    # orange – strings
        comment = _fmt("#6A9955", italic=True)      # green – comments
        preproc = _fmt("#C586C0")                   # purple – preprocessor
        func_call = _fmt("#DCDCAA")                 # yellow – function calls

        # Build rules list: (regex, format)
        self._rules: list[tuple[QRegularExpression, QTextCharFormat]] = []

        # Single-line comment (//)
        self._rules.append((QRegularExpression(r"//[^\n]*"), comment))

        # String literals
        self._rules.append((QRegularExpression(r'"[^"\\]*(\\.[^"\\]*)*"'), string))

        # Preprocessor directives
        self._rules.append((QRegularExpression(r"^\s*#\s*(define|include|ifdef|ifndef|endif|else|elif|undef|pragma)\b"), preproc))

        # Type keywords
        _types = r"\b(float|vector|string|entity|void|int|local)\b"
        self._rules.append((QRegularExpression(_types), kw_type))

        # Field declarations (leading dot)
        self._rules.append((QRegularExpression(r"\.\b\w+\b"), field_color))

        # Control flow
        _flow = r"\b(if|else|while|do|for|return|break|continue|switch|case|default)\b"
        self._rules.append((QRegularExpression(_flow), kw_flow))

        # Special constants / globals
        _special = r"\b(self|other|world|TRUE|FALSE|nil|time|frametime|newmis|deathmatch|coop|teamplay|serverflags|total_secrets|total_monsters|found_secrets|killed_monsters)\b"
        self._rules.append((QRegularExpression(_special), kw_special))

        # Quake built-in functions
        _builtins = (
            r"\b(makevectors|setorigin|setmodel|setsize|setspawnparms|changelevel|"
            r"bprint|sprint|dprint|centerprint|print|objerror|error|"
            r"normalize|vlen|vectoyaw|vectoangles|random|rint|floor|ceil|fabs|"
            r"particle|ambientsound|sound|traceline|aim|"
            r"checkbottom|checkpos|pointcontents|"
            r"stuffcmd|localcmd|newclient|clientcommand|tokenize|argv|"
            r"multicast|WriteAngle|WriteByte|WriteChar|WriteCoord|WriteEntity|"
            r"WriteLong|WriteShort|WriteString|"
            r"precache_model|precache_sound|precache_file|"
            r"spawn|remove|find|nextent|nextclient|"
            r"lightstyle|movetogoal|walkmove|droptofloor|"
            r"logfrag|getinfo|setinfo|"
            r"min|max|bound|pow|sqrt|sin|cos|"
            r"stof|stov|vtos|ftos|itof|ftoi)\b"
        )
        self._rules.append((QRegularExpression(_builtins), builtin))

        # Function-call pattern: word followed by (
        self._rules.append((QRegularExpression(r"\b([A-Za-z_]\w*)\s*(?=\()"), func_call))

        # Numbers (hex, float, int)
        self._rules.append((QRegularExpression(r"\b(0x[0-9A-Fa-f]+|[0-9]*\.[0-9]+([eE][+-]?[0-9]+)?|[0-9]+)\b"), number))

        # Compile all expressions
        for rx, _ in self._rules:
            rx.optimize()

        # Multi-line comment state tracking
        self._comment_start = QRegularExpression(r"/\*")
        self._comment_end = QRegularExpression(r"\*/")
        self._fmt_comment = comment

    def highlightBlock(self, text: str) -> None:
        # Apply single-line rules first
        for rx, fmt in self._rules:
            it = rx.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)

        # Multi-line block comments
        self.setCurrentBlockState(0)
        start = 0
        if self.previousBlockState() != 1:
            m = self._comment_start.match(text)
            start = m.capturedStart() if m.hasMatch() else -1
        while start >= 0:
            end_m = self._comment_end.match(text, start)
            if end_m.hasMatch():
                length = end_m.capturedEnd() - start
                self.setFormat(start, length, self._fmt_comment)
                m = self._comment_start.match(text, start + length)
                start = m.capturedStart() if m.hasMatch() else -1
            else:
                self.setCurrentBlockState(1)
                self.setFormat(start, len(text) - start, self._fmt_comment)
                break
