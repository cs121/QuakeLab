from __future__ import annotations

from pathlib import Path

from core.models.domain import ValidationDiagnostic
from core.parsers.shader_parser import validate_shader
from core.services.settings_service import SettingsService


class ValidationService:
    def __init__(self, settings: SettingsService) -> None:
        self.settings = settings

    def validate_shader_file(self, file_path: Path) -> list[ValidationDiagnostic]:
        """Validate a .shader file and return diagnostics."""
        try:
            content = file_path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return [ValidationDiagnostic(
                file_path=str(file_path),
                line=0,
                severity="error",
                message=f"Could not read file: {file_path}",
            )]

        source_root = self.settings.source_root().resolve()
        return validate_shader(str(file_path), content, source_root)
