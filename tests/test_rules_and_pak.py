from pathlib import Path

from core.rules.build_rules import resolve_actions
from infrastructure.archives.pak import PakArchive


def test_resolve_actions_qc():
    actions = resolve_actions("qc/player.qc", "modified")
    kinds = [a.action_type for a in actions]
    assert "compile_qc" in kinds
    assert "rebuild_pak" in kinds


def test_pak_roundtrip(tmp_path: Path):
    file_a = tmp_path / "a.txt"
    file_a.write_text("abc", encoding="utf-8")
    pak = tmp_path / "pak0.pak"
    archive = PakArchive()
    archive.write(pak, [("docs/a.txt", file_a)])
    entries = archive.read_entries(pak)
    assert entries[0].name == "docs/a.txt"
    assert archive.extract(pak, "docs/a.txt") == b"abc"
