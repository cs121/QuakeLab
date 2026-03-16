from __future__ import annotations

import re
from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class EntityDef:
    classname: str
    description: str = ""
    properties: dict[str, str] = field(default_factory=dict)  # key -> description
    flags: list[str] = field(default_factory=list)


def parse_def_file(path: Path) -> dict[str, EntityDef]:
    """Parse a Quake .def entity definition file.

    Format: blocks starting with /*QUAKED <classname> ... */ followed by property descriptions.
    """
    content = path.read_text(encoding="utf-8", errors="replace")
    return parse_def_content(content)


def parse_def_content(content: str) -> dict[str, EntityDef]:
    """Parse .def content into entity definitions."""
    defs: dict[str, EntityDef] = {}

    # Match /*QUAKED classname (color) spawnflags? ... */
    pattern = re.compile(
        r"/\*QUAKED\s+(\S+)\s+\([\d.\s]+\)\s*(.*?)\*/",
        re.DOTALL,
    )

    for m in pattern.finditer(content):
        classname = m.group(1)
        body = m.group(2).strip()

        lines = body.splitlines()
        description_parts: list[str] = []
        flags: list[str] = []
        properties: dict[str, str] = {}

        for line in lines:
            stripped = line.strip()
            if not stripped:
                continue
            # Spawnflag lines often look like: "FLAG_NAME : description"
            flag_match = re.match(r"^(\w+)\s*:\s*(.*)$", stripped)
            if flag_match:
                flags.append(flag_match.group(1))
                properties[flag_match.group(1)] = flag_match.group(2)
            else:
                description_parts.append(stripped)

        defs[classname] = EntityDef(
            classname=classname,
            description=" ".join(description_parts),
            properties=properties,
            flags=flags,
        )

    return defs


def parse_fgd_file(path: Path) -> dict[str, EntityDef]:
    """Parse a basic .fgd (Forge Game Data) entity definition file.

    Simplified parser - extracts classnames and base properties.
    """
    content = path.read_text(encoding="utf-8", errors="replace")
    return parse_fgd_content(content)


def parse_fgd_content(content: str) -> dict[str, EntityDef]:
    """Parse .fgd content into entity definitions."""
    defs: dict[str, EntityDef] = {}

    # Match @PointClass/@SolidClass ... = classname : "description" [...]
    pattern = re.compile(
        r"@(?:PointClass|SolidClass|BaseClass)[^=]*=\s*(\w+)\s*(?::\s*\"([^\"]*)\")?"
    )

    for m in pattern.finditer(content):
        classname = m.group(1)
        description = m.group(2) or ""
        defs[classname] = EntityDef(classname=classname, description=description)

    return defs
