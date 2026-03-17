from __future__ import annotations

from pathlib import Path

from core.services.build_profile_service import BuildProfile, BuildProfileService
from core.services.settings_service import SettingsService
from infrastructure.db.database import Database


def _make_db(tmp_path: Path) -> Database:
    return Database(tmp_path / ".quakelab" / "quakelab.db")


def test_default_profiles_exist(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    svc = BuildProfileService(db)
    profiles = svc.list_profiles()
    names = [p.name for p in profiles]
    assert "Debug" in names
    assert "Release" in names


def test_get_profile(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    svc = BuildProfileService(db)
    debug = svc.get_profile("Debug")
    assert debug is not None
    assert debug.name == "Debug"
    assert debug.qc_args == "-Wall"
    assert debug.map_build_mode == "fast"


def test_save_and_get_profile(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    svc = BuildProfileService(db)
    profile = BuildProfile(id=0, name="Custom", qc_args="-O2", qbsp_args="-leak",
                           vis_args="", light_args="-extra", map_build_mode="full")
    svc.save_profile(profile)
    loaded = svc.get_profile("Custom")
    assert loaded is not None
    assert loaded.qc_args == "-O2"
    assert loaded.light_args == "-extra"
    assert loaded.map_build_mode == "full"


def test_delete_profile(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    svc = BuildProfileService(db)
    svc.delete_profile("Debug")
    assert svc.get_profile("Debug") is None


def test_apply_profile(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    settings = SettingsService(db, tmp_path)
    svc = BuildProfileService(db)
    release = svc.get_profile("Release")
    assert release is not None
    svc.apply_profile(release, settings)
    assert settings.get("map_build_mode") == "full"
    assert settings.get("active_build_profile") == "Release"


def test_save_profile_upsert(tmp_path: Path) -> None:
    db = _make_db(tmp_path)
    svc = BuildProfileService(db)
    debug = svc.get_profile("Debug")
    assert debug is not None
    debug.qc_args = "-O3"
    svc.save_profile(debug)
    reloaded = svc.get_profile("Debug")
    assert reloaded is not None
    assert reloaded.qc_args == "-O3"
