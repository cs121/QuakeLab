from __future__ import annotations

import threading
import time
from datetime import datetime
from pathlib import Path

from core.models.domain import FileChange
from core.services.build_queue_service import BuildQueueService
from core.services.change_journal_service import ChangeJournalService
from core.services.log_service import LogService
from core.services.settings_service import SettingsService
from core.services.task_resolver_service import TaskResolverService
from infrastructure.filesystem.hashing import sha1_file


class PollingWatchService:
    def __init__(
        self,
        settings: SettingsService,
        journal: ChangeJournalService,
        queue: BuildQueueService,
        resolver: TaskResolverService,
        logs: LogService,
    ) -> None:
        self.settings = settings
        self.journal = journal
        self.queue = queue
        self.resolver = resolver
        self.logs = logs
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._known: dict[str, tuple[str, int, float]] = {}
        self._last_emit: dict[str, float] = {}
        self._debounce_sec = 0.7

    def start(self) -> None:
        if self.settings.get("auto_watch", "1") != "1":
            return
        if self._thread and self._thread.is_alive():
            return
        self._thread = threading.Thread(target=self._loop, daemon=True)
        self._thread.start()
        self.logs.write("INFO", "Watch", "Watcher started")

    def stop(self) -> None:
        self._stop.set()
        if self._thread:
            self._thread.join(timeout=1.0)

    def _loop(self) -> None:
        while not self._stop.is_set():
            try:
                self._scan_once()
            except Exception as exc:  # noqa: BLE001
                self.logs.write("ERROR", "Watch", f"Scan failed: {exc}")
            time.sleep(1.0)

    def _scan_once(self) -> None:
        source_root = self.settings.source_root()
        if not source_root.exists():
            return

        current: dict[str, tuple[str, int, float]] = {}
        for path in source_root.rglob("*"):
            if not path.is_file():
                continue
            rel = path.relative_to(source_root).as_posix()
            if rel.startswith(".quakeforge/"):
                continue
            stat = path.stat()
            digest = sha1_file(path)
            current[rel] = (digest, stat.st_size, stat.st_mtime)

        old_keys = set(self._known)
        new_keys = set(current)

        for rel in new_keys - old_keys:
            self._record(source_root / rel, rel, "created", None, current[rel][0], current[rel][1], current[rel][2])

        for rel in old_keys & new_keys:
            old = self._known[rel]
            new = current[rel]
            if old[0] != new[0] or old[1] != new[1]:
                self._record(source_root / rel, rel, "modified", old[0], new[0], new[1], new[2])

        for rel in old_keys - new_keys:
            old = self._known[rel]
            self._record(source_root / rel, rel, "deleted", old[0], None, old[1], old[2])

        self._known = current

    def _record(self, absolute: Path, rel: str, change_type: str, old_hash: str | None, new_hash: str | None, size: int, mtime: float) -> None:
        now = time.time()
        dedupe_key = f"{change_type}:{rel}:{new_hash}"
        if now - self._last_emit.get(dedupe_key, 0) < self._debounce_sec:
            return
        self._last_emit[dedupe_key] = now

        change = FileChange(
            timestamp=datetime.utcnow(),
            project=self.settings.get("project_name", "QuakeForge"),
            relative_path=rel,
            absolute_path=str(absolute),
            change_type=change_type,
            old_hash=old_hash,
            new_hash=new_hash,
            size=size,
            mtime=mtime,
        )
        self.journal.add(change)
        for action in self.resolver.actions_for_change(rel, change_type):
            self.queue.enqueue(action)
