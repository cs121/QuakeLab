from core.parsers.shader_parser import validate_shader


def test_valid_simple_shader():
    content = """\
textures/myshader
{
    {
        map textures/base.tga
        blendFunc GL_ONE GL_ZERO
    }
}
"""
    diags = validate_shader("test.shader", content)
    assert len(diags) == 0


def test_unclosed_brace():
    content = """\
textures/broken
{
    {
        map textures/test.tga
    }
"""
    diags = validate_shader("test.shader", content)
    assert any(d.severity == "error" and "Unclosed" in d.message for d in diags)


def test_extra_closing_brace():
    content = """\
textures/broken
{
}
}
"""
    diags = validate_shader("test.shader", content)
    assert any(d.severity == "error" and "Unexpected closing brace" in d.message for d in diags)


def test_nesting_too_deep():
    content = """\
textures/deep
{
    {
        {
            map textures/deep.tga
        }
    }
}
"""
    diags = validate_shader("test.shader", content)
    assert any(d.severity == "error" and "too deep" in d.message for d in diags)


def test_unknown_directive_warning():
    content = """\
textures/unknown
{
    foobar_directive 42
}
"""
    diags = validate_shader("test.shader", content)
    assert any(d.severity == "warning" and "Unknown directive" in d.message for d in diags)


def test_texture_not_found(tmp_path):
    content = """\
textures/missing
{
    {
        map textures/nonexistent
    }
}
"""
    diags = validate_shader("test.shader", content, source_root=tmp_path)
    assert any(d.severity == "warning" and "not found" in d.message for d in diags)


def test_texture_found(tmp_path):
    (tmp_path / "textures").mkdir()
    (tmp_path / "textures" / "exists.tga").touch()
    content = """\
textures/found
{
    {
        map textures/exists.tga
    }
}
"""
    diags = validate_shader("test.shader", content, source_root=tmp_path)
    assert not any(d.severity == "warning" and "not found" in d.message for d in diags)


def test_special_texture_refs():
    content = """\
textures/special
{
    {
        map $lightmap
    }
}
"""
    diags = validate_shader("test.shader", content)
    assert len(diags) == 0


def test_empty_file():
    diags = validate_shader("empty.shader", "")
    assert len(diags) == 0
