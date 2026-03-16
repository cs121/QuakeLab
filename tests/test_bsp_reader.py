import struct

import pytest

from infrastructure.formats.bsp import BspFormatError, read_bsp_info


def _make_minimal_bsp(tmp_path, entities=b"", textures=None):
    """Create a minimal valid Quake 1 BSP file for testing."""
    # Header: version (4 bytes) + 15 lumps (each 8 bytes = offset + length)
    header_size = 4 + 15 * 8
    data = bytearray()

    # Version 29
    data.extend(struct.pack("<i", 29))

    # Build lump data sections
    sections = []
    current_offset = header_size

    # Lump 0: entities
    sections.append(entities)
    # Lump 1: planes (empty)
    sections.append(b"")
    # Lump 2: textures
    if textures is None:
        # Empty texture lump with count = 0
        textures = struct.pack("<i", 0)
    sections.append(textures)
    # Lumps 3-14 (empty)
    for _ in range(12):
        sections.append(b"")

    # Calculate offsets and build lump directory
    offset = header_size
    for section in sections:
        data.extend(struct.pack("<ii", offset, len(section)))
        offset += len(section)

    # Append all section data
    for section in sections:
        data.extend(section)

    path = tmp_path / "test.bsp"
    path.write_bytes(bytes(data))
    return path


def test_read_empty_bsp(tmp_path):
    path = _make_minimal_bsp(tmp_path)
    info = read_bsp_info(path)
    assert info.version == 29
    assert info.entity_count == 0
    assert info.texture_names == []


def test_read_entities(tmp_path):
    entities = b'{\n"classname" "worldspawn"\n}\n{\n"classname" "light"\n}\n\x00'
    path = _make_minimal_bsp(tmp_path, entities=entities)
    info = read_bsp_info(path)
    assert info.entity_count == 2
    assert '"classname" "worldspawn"' in info.raw_entities


def test_read_textures(tmp_path):
    # Build a simple texture lump: count + offsets + MIP texture headers
    count = 2
    # Each offset points to a MIP texture header (name is 16 bytes)
    header_start = 4 + count * 4  # after count + offset table
    tex_data = struct.pack("<i", count)
    tex_data += struct.pack("<i", header_start)  # offset for texture 0
    tex_data += struct.pack("<i", header_start + 40)  # offset for texture 1

    # MIP texture header: 16-byte name + 24 bytes (width, height, 4 mip offsets)
    name1 = b"brick01\x00" + b"\x00" * 8  # 16 bytes
    name1 += b"\x00" * 24  # rest of header
    name2 = b"stone02\x00" + b"\x00" * 8
    name2 += b"\x00" * 24
    tex_data += name1 + name2

    path = _make_minimal_bsp(tmp_path, textures=tex_data)
    info = read_bsp_info(path)
    assert "brick01" in info.texture_names
    assert "stone02" in info.texture_names


def test_reject_wrong_version(tmp_path):
    data = struct.pack("<i", 99) + b"\x00" * (15 * 8)
    path = tmp_path / "bad.bsp"
    path.write_bytes(data)
    with pytest.raises(BspFormatError, match="Unsupported BSP version"):
        read_bsp_info(path)


def test_reject_too_small(tmp_path):
    path = tmp_path / "tiny.bsp"
    path.write_bytes(b"\x00" * 10)
    with pytest.raises(BspFormatError, match="too small"):
        read_bsp_info(path)
