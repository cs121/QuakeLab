from __future__ import annotations

import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class ProcessResult:
    code: int
    stdout: str
    stderr: str


class ProcessRunner:
    def run(self, executable: str, args: list[str], cwd: Path | None = None) -> ProcessResult:
        proc = subprocess.run(
            [executable, *args],
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            check=False,
        )
        return ProcessResult(proc.returncode, proc.stdout, proc.stderr)
