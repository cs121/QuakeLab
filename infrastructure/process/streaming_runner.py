from __future__ import annotations

import subprocess
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from pathlib import Path

from infrastructure.process.runner import ProcessResult


@dataclass(slots=True)
class StreamingResult:
    code: int
    stdout: str
    stderr: str
    lines: list[tuple[str, str]] = field(default_factory=list)

    def as_process_result(self) -> ProcessResult:
        return ProcessResult(self.code, self.stdout, self.stderr)


class StreamingProcessRunner:
    """Runs external processes with line-by-line streaming output via callback."""

    def run(
        self,
        executable: str,
        args: list[str],
        cwd: Path | None = None,
        on_line: Callable[[str, str], None] | None = None,
    ) -> StreamingResult:
        proc = subprocess.Popen(
            [executable, *args],
            cwd=str(cwd) if cwd else None,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )

        stdout_lines: list[str] = []
        stderr_lines: list[str] = []
        all_lines: list[tuple[str, str]] = []

        def _read_stream(stream, stream_name: str, collector: list[str]) -> None:
            assert stream is not None
            for line in stream:
                stripped = line.rstrip("\n\r")
                collector.append(stripped)
                all_lines.append((stream_name, stripped))
                if on_line:
                    on_line(stream_name, stripped)

        stdout_thread = threading.Thread(
            target=_read_stream, args=(proc.stdout, "stdout", stdout_lines), daemon=True
        )
        stderr_thread = threading.Thread(
            target=_read_stream, args=(proc.stderr, "stderr", stderr_lines), daemon=True
        )
        stdout_thread.start()
        stderr_thread.start()
        stdout_thread.join()
        stderr_thread.join()
        proc.wait()

        return StreamingResult(
            code=proc.returncode,
            stdout="\n".join(stdout_lines),
            stderr="\n".join(stderr_lines),
            lines=all_lines,
        )


def run_detached(
    executable: str,
    args: list[str],
    cwd: Path | None = None,
) -> subprocess.Popen:
    """Launch a process without waiting for completion (fire-and-forget)."""
    return subprocess.Popen(
        [executable, *args],
        cwd=str(cwd) if cwd else None,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
        stdin=subprocess.DEVNULL,
    )
