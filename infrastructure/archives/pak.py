from __future__ import annotations

import io
import struct
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class PakEntry:
    name: str
    offset: int
    size: int


class PakArchive:
    HEADER = b"PACK"

    def read_entries(self, pak_path: Path) -> list[PakEntry]:
        with pak_path.open("rb") as f:
            magic = f.read(4)
            if magic != self.HEADER:
                raise ValueError("Not a Quake PAK file")
            dir_offset, dir_size = struct.unpack("<ii", f.read(8))
            f.seek(dir_offset)
            data = f.read(dir_size)
        entries = []
        for i in range(0, len(data), 64):
            raw_name, offset, size = struct.unpack("<56sii", data[i : i + 64])
            name = raw_name.split(b"\x00", 1)[0].decode("ascii", errors="ignore")
            entries.append(PakEntry(name, offset, size))
        return entries

    def extract(self, pak_path: Path, name: str) -> bytes:
        entries = self.read_entries(pak_path)
        with pak_path.open("rb") as f:
            for entry in entries:
                if entry.name == name:
                    f.seek(entry.offset)
                    return f.read(entry.size)
        raise KeyError(name)

    def write(self, output_path: Path, files: list[tuple[str, Path]]) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        temp = output_path.with_suffix(output_path.suffix + ".tmp")
        content = io.BytesIO()
        directory = io.BytesIO()
        offset = 12

        for pak_name, fs_path in files:
            data = fs_path.read_bytes()
            content.write(data)
            encoded_name = pak_name.encode("ascii", errors="ignore")[:56]
            encoded_name = encoded_name + (b"\x00" * (56 - len(encoded_name)))
            directory.write(struct.pack("<56sii", encoded_name, offset, len(data)))
            offset += len(data)

        with temp.open("wb") as f:
            f.write(self.HEADER)
            f.write(struct.pack("<ii", 12 + content.getbuffer().nbytes, directory.getbuffer().nbytes))
            f.write(content.getvalue())
            f.write(directory.getvalue())

        temp.replace(output_path)
