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


def test_reset_workspace_rebuilds_database_and_resets_paths(tmp_path: Path):
    project_root = tmp_path / "workbench"
    db = Database(project_root / ".quakelab" / "quakelab.db")
    settings = SettingsService(db, project_root)

    settings.set("source_root", "custom_src")
    settings.set("build_root", "custom_build")
    settings.set("deploy_root", "custom_deploy")
    settings.set("qc_executable", "/tools/qc")
    db.execute(
        "INSERT INTO build_queue(action_type, relative_path, payload) VALUES(?, ?, ?)",
        ("compile_qc", "progs.src", "{}"),
    )

    for folder in ["custom_src", "custom_build", "custom_deploy"]:
        path = project_root / folder
        path.mkdir(parents=True, exist_ok=True)
        (path / "temp.txt").write_text("stale", encoding="utf-8")

    settings.reset_workspace()

    assert settings.get("source_root") == "src"
    assert settings.get("build_root") == "build"
    assert settings.get("deploy_root") == "deploy"
    assert settings.get("qc_executable", "") == ""

    assert not (project_root / "custom_src").exists()
    assert not (project_root / "custom_build").exists()
    assert not (project_root / "custom_deploy").exists()

    assert (project_root / "src").is_dir()
    assert (project_root / "build").is_dir()
    assert (project_root / "deploy").is_dir()

    queue_count = db.query("SELECT COUNT(*) AS total FROM build_queue")[0]["total"]
    assert queue_count == 0
