from __future__ import annotations

import shutil

from core.services.log_service import LogService
from core.services.settings_service import SettingsService


class DeployService:
    def __init__(self, settings: SettingsService, logs: LogService) -> None:
        self.settings = settings
        self.logs = logs

    def deploy_pak(self) -> bool:
        source = self.settings.pak_output_path()
        target = self.settings.deploy_root() / source.name
        if not source.exists():
            self.logs.write("ERROR", "Deploy", f"PAK not found: {source}")
            return False
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)
        self.logs.write("INFO", "Deploy", f"Copied {source} -> {target}")
        return True
