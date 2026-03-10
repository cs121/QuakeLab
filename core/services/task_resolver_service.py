from __future__ import annotations

from core.models.domain import BuildAction
from core.rules.build_rules import resolve_actions
from core.services.settings_service import SettingsService


class TaskResolverService:
    def __init__(self, settings_service: SettingsService) -> None:
        self.settings_service = settings_service

    def actions_for_change(self, relative_path: str, change_type: str) -> list[BuildAction]:
        return resolve_actions(relative_path, change_type)
