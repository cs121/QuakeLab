from __future__ import annotations

import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from core.services.project_service import ProjectService
from core.services.settings_service import SettingsService
from core.services.change_journal_service import ChangeJournalService
from core.services.build_queue_service import BuildQueueService
from core.services.task_resolver_service import TaskResolverService
from core.services.compiler_service import CompilerService
from core.services.pack_service import PackService
from core.services.deploy_service import DeployService
from core.services.launch_service import LaunchService
from core.services.preview_service import PreviewService
from core.services.log_service import LogService
from infrastructure.db.database import Database
from infrastructure.filesystem.watcher import PollingWatchService
from infrastructure.archives.pak import PakArchive
from infrastructure.process.runner import ProcessRunner
from ui.main_window import MainWindow


def run() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("QuakeLab")

    project_root = Path.cwd()
    db_path = project_root / ".quakelab" / "quakelab.db"
    db = Database(db_path)

    project_service = ProjectService(db, project_root)
    settings_service = SettingsService(db, project_root)
    log_service = LogService(db)
    journal = ChangeJournalService(db)
    build_queue = BuildQueueService(db)
    resolver = TaskResolverService(settings_service)
    compiler = CompilerService(settings_service, ProcessRunner(), log_service)
    pack_service = PackService(settings_service, PakArchive(), log_service)
    deploy_service = DeployService(settings_service, log_service)
    launch_service = LaunchService(settings_service, log_service)
    watcher = PollingWatchService(settings_service, journal, build_queue, resolver, log_service)
    preview_service = PreviewService()

    window = MainWindow(
        project_service=project_service,
        settings_service=settings_service,
        change_journal=journal,
        build_queue=build_queue,
        compiler_service=compiler,
        pack_service=pack_service,
        deploy_service=deploy_service,
        launch_service=launch_service,
        watch_service=watcher,
        preview_service=preview_service,
        log_service=log_service,
    )
    window.show()
    watcher.start()
    rc = app.exec()
    watcher.stop()
    return rc
