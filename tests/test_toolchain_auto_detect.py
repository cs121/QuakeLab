from __future__ import annotations

from pathlib import Path

from core.services.settings_service import SettingsService
from core.services.toolchain_check_service import ToolchainCheckService
from infrastructure.db.database import Database


def test_auto_detect_returns_dict(tmp_path: Path) -> None:
    db = Database(tmp_path / ".quakelab" / "quakelab.db")
    settings = SettingsService(db, tmp_path)
    checker = ToolchainCheckService(settings)
    result = checker.auto_detect_tools()
    assert isinstance(result, dict)
    # We can't guarantee any tools are installed, but the method should not crash
    for key in result:
        assert key in {"qc_executable", "qbsp_executable", "vis_executable", "light_executable", "engine_exe"}


def test_auto_detect_finds_common_tools(tmp_path: Path) -> None:
    """If we create a fake tool in a known location, it should be found."""
    # Create a fake tool in a temp directory added to PATH
    bin_dir = tmp_path / "bin"
    bin_dir.mkdir()
    fake_tool = bin_dir / "fteqcc"
    fake_tool.write_text("#!/bin/sh\necho fake")
    fake_tool.chmod(0o755)

    db = Database(tmp_path / ".quakelab" / "quakelab.db")
    settings = SettingsService(db, tmp_path)
    checker = ToolchainCheckService(settings)

    import os
    old_path = os.environ.get("PATH", "")
    os.environ["PATH"] = f"{bin_dir}:{old_path}"
    try:
        result = checker.auto_detect_tools()
        assert "qc_executable" in result
        assert "fteqcc" in result["qc_executable"]
    finally:
        os.environ["PATH"] = old_path
