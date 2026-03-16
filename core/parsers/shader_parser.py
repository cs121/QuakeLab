from __future__ import annotations

from pathlib import Path

from core.models.domain import ValidationDiagnostic

# Known Quake 1/3 shader directives (stage-level and shader-level)
_SHADER_DIRECTIVES = {
    "surfaceparm", "cull", "deformvertexes", "tesssize", "nopicmip",
    "nomipmaps", "polygonoffset", "portal", "sort", "fogparms",
    "skyparms", "light", "q3map_sun", "q3map_surfacelight",
    "q3map_lightimage", "q3map_globaltexture", "q3map_backsplash",
    "qer_editorimage", "qer_nocarve", "qer_trans",
}

_STAGE_DIRECTIVES = {
    "map", "clampmap", "animmap", "blendfunc", "rgbgen", "alphagen",
    "tcgen", "tcmod", "depthfunc", "depthwrite", "alphafunc",
    "detail", "lightmap",
}

_ALL_KNOWN = _SHADER_DIRECTIVES | _STAGE_DIRECTIVES


def validate_shader(
    file_path: str,
    content: str,
    source_root: Path | None = None,
) -> list[ValidationDiagnostic]:
    """Validate a Quake .shader file and return diagnostics."""
    diags: list[ValidationDiagnostic] = []
    depth = 0
    max_depth = 0
    lines = content.splitlines()

    for line_num, raw_line in enumerate(lines, start=1):
        line = raw_line.strip()

        # Skip empty lines and comments
        if not line or line.startswith("//"):
            continue

        # Handle braces
        if line == "{":
            depth += 1
            max_depth = max(max_depth, depth)
            if depth > 2:
                diags.append(ValidationDiagnostic(
                    file_path=file_path,
                    line=line_num,
                    severity="error",
                    message=f"Nesting too deep (depth {depth}), maximum is 2",
                ))
            continue

        if line == "}":
            if depth <= 0:
                diags.append(ValidationDiagnostic(
                    file_path=file_path,
                    line=line_num,
                    severity="error",
                    message="Unexpected closing brace - no matching opening brace",
                ))
            else:
                depth -= 1
            continue

        # At depth 0: should be a shader name
        if depth == 0:
            continue

        # At depth 1 or 2: parse directives
        parts = line.split()
        if not parts:
            continue

        directive = parts[0].lower()

        # Check for unknown directives (only warn, don't error)
        if directive not in _ALL_KNOWN and not directive.startswith(("$", "//")):
            diags.append(ValidationDiagnostic(
                file_path=file_path,
                line=line_num,
                severity="warning",
                message=f"Unknown directive: {parts[0]}",
            ))

        # Check texture references
        if directive == "map" and len(parts) >= 2:
            tex_ref = parts[1]
            if tex_ref.startswith("$"):  # Special references like $lightmap
                continue
            if source_root is not None:
                _check_texture_exists(file_path, line_num, tex_ref, source_root, diags)

    # Check unclosed braces
    if depth > 0:
        diags.append(ValidationDiagnostic(
            file_path=file_path,
            line=len(lines),
            severity="error",
            message=f"Unclosed brace(s): {depth} still open at end of file",
        ))

    return diags


def _check_texture_exists(
    file_path: str,
    line: int,
    tex_ref: str,
    source_root: Path,
    diags: list[ValidationDiagnostic],
) -> None:
    """Check if a referenced texture exists in the source tree."""
    # Texture refs may or may not include extension
    candidates = [
        source_root / tex_ref,
        source_root / f"{tex_ref}.tga",
        source_root / f"{tex_ref}.jpg",
        source_root / f"{tex_ref}.png",
    ]
    if not any(c.exists() for c in candidates):
        diags.append(ValidationDiagnostic(
            file_path=file_path,
            line=line,
            severity="warning",
            message=f"Texture not found: {tex_ref}",
        ))
