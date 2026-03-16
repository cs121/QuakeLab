import struct

import pytest

from infrastructure.formats.wad import WadFormatError, read_wad, texture_to_rgb


def _make_wad2(tmp_path, textures=None):
    """Create a minimal WAD2 file for testing."""
    if textures is None:
        textures = []

    # Build texture data sections
    tex_data_sections = []
    header_size = 12  # magic + num_entries + dir_offset
    current_offset = header_size

    for name, width, height, pixels in textures:
        # MIP texture header: 16-byte name + width + height + 4 mip offsets
        name_bytes = name.encode("ascii")[:16].ljust(16, b"\x00")
        mip0_offset = 40  # offset from start of this texture entry
        mip_header = struct.pack(
            "<16sII4I",
            name_bytes, width, height,
            mip0_offset, 0, 0, 0,  # only mip0 used
        )
        tex_data = mip_header + pixels
        tex_data_sections.append((current_offset, tex_data))
        current_offset += len(tex_data)

    dir_offset = current_offset

    # Build directory entries
    dir_data = b""
    for i, (name, width, height, pixels) in enumerate(textures):
        offset = tex_data_sections[i][0]
        size = len(tex_data_sections[i][1])
        name_bytes = name.encode("ascii")[:16].ljust(16, b"\x00")
        # offset, disk_size, size, 2 pad bytes, type (0x44), compression (0), name
        dir_data += struct.pack("<iii2xBB16s", offset, size, size, 0x44, 0, name_bytes)

    # Header
    data = b"WAD2"
    data += struct.pack("<ii", len(textures), dir_offset)

    # Texture data
    for _, section in tex_data_sections:
        data += section

    # Directory
    data += dir_data

    path = tmp_path / "test.wad"
    path.write_bytes(data)
    return path


def test_read_empty_wad(tmp_path):
    path = _make_wad2(tmp_path)
    info = read_wad(path)
    assert len(info.textures) == 0


def test_read_single_texture(tmp_path):
    # 4x4 texture, all palette index 15
    pixels = bytes([15] * 16)
    path = _make_wad2(tmp_path, [("brick01", 4, 4, pixels)])
    info = read_wad(path)
    assert len(info.textures) == 1
    assert info.textures[0].name == "brick01"
    assert info.textures[0].width == 4
    assert info.textures[0].height == 4
    assert len(info.textures[0].pixels) == 16


def test_read_multiple_textures(tmp_path):
    pix1 = bytes([0] * 16)
    pix2 = bytes([1] * 64)
    path = _make_wad2(tmp_path, [("tex_a", 4, 4, pix1), ("tex_b", 8, 8, pix2)])
    info = read_wad(path)
    assert len(info.textures) == 2
    assert info.textures[0].name == "tex_a"
    assert info.textures[1].name == "tex_b"


def test_texture_to_rgb():
    from infrastructure.formats.wad import WadTexture
    tex = WadTexture(name="test", width=2, height=2, pixels=bytes([0, 1, 2, 15]))
    rgb = texture_to_rgb(tex)
    assert len(rgb) == 12  # 4 pixels * 3 channels


def test_reject_invalid_magic(tmp_path):
    path = tmp_path / "bad.wad"
    path.write_bytes(b"WAD3" + b"\x00" * 8)
    with pytest.raises(WadFormatError, match="Invalid WAD magic"):
        read_wad(path)


def test_reject_too_small(tmp_path):
    path = tmp_path / "tiny.wad"
    path.write_bytes(b"\x00" * 5)
    with pytest.raises(WadFormatError, match="too small"):
        read_wad(path)
