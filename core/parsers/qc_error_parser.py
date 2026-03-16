from __future__ import annotations

import re

from core.models.domain import CompilerDiagnostic

# fteqcc:  "file.qc:123: error: some message"
# gmqcc:   "file.qc:123:45: error: some message"
# Also handles "warning" severity.
_PATTERN = re.compile(
    r"^(.+?):(\d+)(?::(\d+))?:\s*(error|warning):\s*(.+)$",
    re.IGNORECASE,
)

# fteqcc sometimes uses: "file.qc:123: unknown value 'x'"  (no error/warning prefix)
_FALLBACK_PATTERN = re.compile(
    r"^(.+?):(\d+):\s+(.+)$",
)


def parse_diagnostics(output: str) -> list[CompilerDiagnostic]:
    """Parse compiler output into structured diagnostics."""
    results: list[CompilerDiagnostic] = []
    for line in output.splitlines():
        line = line.strip()
        if not line:
            continue
        m = _PATTERN.match(line)
        if m:
            results.append(
                CompilerDiagnostic(
                    file_path=m.group(1),
                    line=int(m.group(2)),
                    column=int(m.group(3)) if m.group(3) else None,
                    severity=m.group(4).lower(),
                    message=m.group(5),
                )
            )
            continue
        m = _FALLBACK_PATTERN.match(line)
        if m and _looks_like_source_path(m.group(1)):
            results.append(
                CompilerDiagnostic(
                    file_path=m.group(1),
                    line=int(m.group(2)),
                    column=None,
                    severity="error",
                    message=m.group(3),
                )
            )
    return results


def _looks_like_source_path(text: str) -> bool:
    """Heuristic: path-like string ending in a known extension."""
    lower = text.lower().strip()
    return lower.endswith((".qc", ".src", ".h", ".qh"))
