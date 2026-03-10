from pathlib import Path

from core.services.settings_service import SettingsService
from infrastructure.db.database import Database


def test_relative_build_root_is_resolved_next_to_absolute_source_root(tmp_path: Path):
    project_root = tmp_path / "workbench"
    db = Database(project_root / ".quakelab" / "quakelab.db")
    settings = SettingsService(db, project_root)

    source_root = tmp_path / "QuakeLab"
    settings.set("source_root", str(source_root))

    assert settings.source_root() == source_root.resolve()
    assert settings.build_root() == (source_root.parent / "build").resolve()
    assert settings.pak_output_path() == (source_root.parent / "build/pak0.pak").resolve()
