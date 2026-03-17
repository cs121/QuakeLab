from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from core.services.compiler_service import CompilerService
from core.services.settings_service import SettingsService
from infrastructure.db.database import Database


def test_compile_all_maps_empty(tmp_path: Path) -> None:
    """compile_all_maps returns empty list when no .map files exist."""
    db = Database(tmp_path / ".quakelab" / "quakelab.db")
    settings = SettingsService(db, tmp_path)
    src = tmp_path / "src"
    src.mkdir()
    settings.set("source_root", str(src))
    compiler = CompilerService(settings, MagicMock(), MagicMock())
    results = compiler.compile_all_maps()
    assert results == []


def test_compile_all_maps_streaming_empty(tmp_path: Path) -> None:
    """compile_all_maps_streaming returns empty list when no .map files exist."""
    db = Database(tmp_path / ".quakelab" / "quakelab.db")
    settings = SettingsService(db, tmp_path)
    src = tmp_path / "src"
    src.mkdir()
    settings.set("source_root", str(src))
    compiler = CompilerService(settings, MagicMock(), MagicMock())
    results = compiler.compile_all_maps_streaming()
    assert results == []
