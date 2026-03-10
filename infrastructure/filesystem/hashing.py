from __future__ import annotations

import hashlib
from pathlib import Path


def sha1_file(path: Path) -> str:
    hasher = hashlib.sha1()
    with path.open("rb") as f:
        for chunk in iter(lambda: f.read(1024 * 512), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
