from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path


@dataclass(slots=True)
class PointfileData:
    points: list[tuple[float, float, float]] = field(default_factory=list)


def parse_pointfile(path: Path) -> PointfileData:
    """Parse a Quake .pts pointfile (one 'x y z' coordinate per line)."""
    data = PointfileData()
    text = path.read_text(encoding="utf-8", errors="replace")
    for line in text.splitlines():
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        parts = line.split()
        if len(parts) >= 3:
            try:
                x, y, z = float(parts[0]), float(parts[1]), float(parts[2])
                data.points.append((x, y, z))
            except ValueError:
                continue
    return data
