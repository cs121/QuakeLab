from pathlib import Path

import pytest

from infrastructure.archives.pak import PakArchive, PakFormatError, PakValidationError


def test_write_and_read_minimal_pak(tmp_path: Path):
    src = tmp_path / "one.txt"
    src.write_bytes(b"abc")
    pak_path = tmp_path / "pak0.pak"

    archive = PakArchive()
    archive.write(pak_path, [("docs/one.txt", src)])

    entries = archive.read_entries(pak_path)
    assert len(entries) == 1
    assert entries[0].name == "docs/one.txt"
    assert archive.extract(pak_path, "docs/one.txt") == b"abc"


def test_write_multiple_files(tmp_path: Path):
    first = tmp_path / "a.bin"
    second = tmp_path / "b.bin"
    first.write_bytes(b"A" * 10)
    second.write_bytes(b"B" * 20)

    pak_path = tmp_path / "pak0.pak"
    archive = PakArchive()
    archive.write(pak_path, [("textures/a.bin", first), ("textures/b.bin", second)])

    names = [entry.name for entry in archive.read_entries(pak_path)]
    assert names == ["textures/a.bin", "textures/b.bin"]


def test_write_empty_pak(tmp_path: Path):
    pak_path = tmp_path / "empty.pak"
    archive = PakArchive()

    archive.write(pak_path, [])

    assert archive.read_entries(pak_path) == []


def test_reject_too_long_pak_path(tmp_path: Path):
    src = tmp_path / "long.txt"
    src.write_text("x", encoding="utf-8")
    long_name = "a" * 57

    with pytest.raises(PakValidationError, match="maximum is 56"):
        PakArchive().write(tmp_path / "pak0.pak", [(long_name, src)])


def test_reject_duplicate_target_path(tmp_path: Path):
    one = tmp_path / "one.txt"
    two = tmp_path / "two.txt"
    one.write_text("1", encoding="utf-8")
    two.write_text("2", encoding="utf-8")

    with pytest.raises(PakValidationError, match="Duplicate PAK target path"):
        PakArchive().write(tmp_path / "pak0.pak", [("same/path.txt", one), ("same/path.txt", two)])


def test_reject_output_pak_as_input(tmp_path: Path):
    output = tmp_path / "pak0.pak"
    output.write_bytes(b"seed")

    with pytest.raises(PakValidationError, match="output PAK itself"):
        PakArchive().write(output, [("pak0.pak", output)])


def test_missing_input_file_has_clear_error(tmp_path: Path):
    missing = tmp_path / "missing.bin"

    with pytest.raises(PakValidationError, match="does not exist"):
        PakArchive().write(tmp_path / "pak0.pak", [("textures/missing.bin", missing)])


def test_keep_previous_pak_when_write_fails(tmp_path: Path):
    output = tmp_path / "pak0.pak"
    archive = PakArchive()
    valid_src = tmp_path / "good.txt"
    valid_src.write_bytes(b"good")
    archive.write(output, [("good.txt", valid_src)])
    before = output.read_bytes()

    bad_src = tmp_path / "missing.txt"
    with pytest.raises(PakValidationError):
        archive.write(output, [("missing.txt", bad_src)])

    assert output.read_bytes() == before


def test_reject_malformed_directory(tmp_path: Path):
    pak_path = tmp_path / "broken.pak"
    pak_path.write_bytes(b"PACK" + (12).to_bytes(4, "little", signed=True) + (1).to_bytes(4, "little", signed=True))

    with pytest.raises(PakFormatError, match="multiple"):
        PakArchive().read_entries(pak_path)
