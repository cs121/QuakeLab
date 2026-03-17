from __future__ import annotations

from pathlib import Path

from core.parsers.pointfile_parser import parse_pointfile


def test_parse_basic_pointfile(tmp_path: Path) -> None:
    pts = tmp_path / "leak.pts"
    pts.write_text("0 0 0\n100 200 300\n-50.5 10.2 0\n")
    data = parse_pointfile(pts)
    assert len(data.points) == 3
    assert data.points[0] == (0.0, 0.0, 0.0)
    assert data.points[1] == (100.0, 200.0, 300.0)
    assert data.points[2] == (-50.5, 10.2, 0.0)


def test_parse_empty_pointfile(tmp_path: Path) -> None:
    pts = tmp_path / "empty.pts"
    pts.write_text("")
    data = parse_pointfile(pts)
    assert data.points == []


def test_parse_pointfile_skips_comments_and_blanks(tmp_path: Path) -> None:
    pts = tmp_path / "comments.pts"
    pts.write_text("// comment\n\n1 2 3\n// another\n4 5 6\n")
    data = parse_pointfile(pts)
    assert len(data.points) == 2
    assert data.points[0] == (1.0, 2.0, 3.0)
    assert data.points[1] == (4.0, 5.0, 6.0)


def test_parse_pointfile_skips_invalid_lines(tmp_path: Path) -> None:
    pts = tmp_path / "bad.pts"
    pts.write_text("1 2 3\nnot a point\n4 5 6\n")
    data = parse_pointfile(pts)
    assert len(data.points) == 2
