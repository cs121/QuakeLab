from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(slots=True)
class MapEntity:
    line: int
    properties: dict[str, str] = field(default_factory=dict)

    @property
    def classname(self) -> str:
        return self.properties.get("classname", "")


def parse_entities(content: str) -> list[MapEntity]:
    """Parse entity blocks from a Quake .map file."""
    entities: list[MapEntity] = []
    current: MapEntity | None = None
    depth = 0

    for line_num, raw_line in enumerate(content.splitlines(), start=1):
        line = raw_line.strip()

        if line == "{":
            depth += 1
            if depth == 1:
                current = MapEntity(line=line_num)
            continue

        if line == "}":
            depth -= 1
            if depth == 0 and current is not None:
                entities.append(current)
                current = None
            continue

        # Parse key-value pairs at entity level (depth == 1)
        if depth == 1 and current is not None:
            m = re.match(r'^"([^"]+)"\s+"([^"]*)"$', line)
            if m:
                current.properties[m.group(1)] = m.group(2)

    return entities
