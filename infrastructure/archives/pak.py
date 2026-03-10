from __future__ import annotations

import struct
import tempfile
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

PAK_MAGIC = b"PACK"
PAK_HEADER_STRUCT = struct.Struct("<4sii")
PAK_DIRECTORY_ENTRY_STRUCT = struct.Struct("<56sii")
PAK_DIRECTORY_ENTRY_SIZE = PAK_DIRECTORY_ENTRY_STRUCT.size
PAK_NAME_MAX_BYTES = 56
PAK_I32_MIN = -(2**31)
PAK_I32_MAX = 2**31 - 1


class PakError(Exception):
    """Base class for PAK domain errors."""


class PakValidationError(PakError):
    """Raised when writer input is invalid."""


class PakBuildError(PakError):
    """Raised when creating a PAK archive fails."""


class PakFormatError(PakError):
    """Raised when a PAK file is malformed."""


@dataclass(slots=True)
class PakEntry:
    name: str
    offset: int
    size: int


@dataclass(slots=True)
class _PakBuildEntry:
    name: str
    encoded_name: bytes
    source_path: Path
    offset: int
    size: int


def validate_i32(value: int, field_name: str, *, non_negative: bool = True) -> int:
    if not isinstance(value, int):
        raise PakValidationError(f"{field_name} must be an int, got {type(value).__name__}")
    if value < PAK_I32_MIN or value > PAK_I32_MAX:
        raise PakValidationError(
            f"{field_name}={value} out of 32-bit signed range "
            f"[{PAK_I32_MIN}, {PAK_I32_MAX}]"
        )
    if non_negative and value < 0:
        raise PakValidationError(f"{field_name} must not be negative: {value}")
    return value


def validate_pak_path(raw_path: str) -> str:
    if not isinstance(raw_path, str):
        raise PakValidationError(f"PAK path must be a string, got {type(raw_path).__name__}")
    normalized = raw_path.strip().replace("\\", "/")
    if not normalized:
        raise PakValidationError("PAK path must not be empty")
    if ":" in normalized.split("/")[0]:
        raise PakValidationError(f"PAK path must not contain Windows drive prefixes: {raw_path!r}")
    if normalized.startswith("/"):
        raise PakValidationError(f"PAK path must be relative: {raw_path!r}")

    path_obj = PurePosixPath(normalized)
    if path_obj.is_absolute() or any(part in ("", ".", "..") for part in path_obj.parts):
        raise PakValidationError(f"Invalid PAK path: {raw_path!r}")

    try:
        encoded = normalized.encode("ascii")
    except UnicodeEncodeError as exc:
        raise PakValidationError(f"PAK path must be ASCII: {raw_path!r}") from exc

    if len(encoded) > PAK_NAME_MAX_BYTES:
        raise PakValidationError(
            f"PAK path '{normalized}' is {len(encoded)} bytes, maximum is {PAK_NAME_MAX_BYTES}"
        )
    return normalized


class PakArchive:
    HEADER = PAK_MAGIC

    def read_entries(self, pak_path: Path) -> list[PakEntry]:
        with pak_path.open("rb") as f:
            header_data = f.read(PAK_HEADER_STRUCT.size)
            if len(header_data) != PAK_HEADER_STRUCT.size:
                raise PakFormatError(f"PAK header too short in {pak_path}")
            magic, dir_offset, dir_length = PAK_HEADER_STRUCT.unpack(header_data)
            if magic != self.HEADER:
                raise PakFormatError(f"Not a Quake PAK file: {pak_path}")

            try:
                validate_i32(dir_offset, "dir_offset")
                validate_i32(dir_length, "dir_length")
            except PakValidationError as exc:
                raise PakFormatError(str(exc)) from exc

            if dir_length % PAK_DIRECTORY_ENTRY_SIZE != 0:
                raise PakFormatError(
                    f"Invalid directory length {dir_length}; must be multiple of {PAK_DIRECTORY_ENTRY_SIZE}"
                )

            file_size = pak_path.stat().st_size
            if dir_offset + dir_length > file_size:
                raise PakFormatError(
                    f"Directory points beyond EOF: dir_offset={dir_offset}, "
                    f"dir_length={dir_length}, file_size={file_size}"
                )

            f.seek(dir_offset)
            data = f.read(dir_length)

        entries = []
        for index in range(0, len(data), PAK_DIRECTORY_ENTRY_SIZE):
            raw_name, offset, size = PAK_DIRECTORY_ENTRY_STRUCT.unpack(
                data[index : index + PAK_DIRECTORY_ENTRY_SIZE]
            )
            name_bytes = raw_name.split(b"\x00", 1)[0]
            try:
                name = name_bytes.decode("ascii")
            except UnicodeDecodeError as exc:
                raise PakFormatError(
                    f"Directory entry has non-ASCII name at index {index // PAK_DIRECTORY_ENTRY_SIZE}"
                ) from exc

            try:
                validate_i32(offset, f"entry[{name}].offset")
                validate_i32(size, f"entry[{name}].size")
            except PakValidationError as exc:
                raise PakFormatError(str(exc)) from exc
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

    def _build_entries(self, output_path: Path, files: list[tuple[str, Path]]) -> list[_PakBuildEntry]:
        if files is None:
            raise PakValidationError("files must not be None")

        resolved_output = output_path.resolve()
        entries: list[_PakBuildEntry] = []
        seen_names: set[str] = set()
        offset = PAK_HEADER_STRUCT.size

        for item in files:
            if not isinstance(item, tuple) or len(item) != 2:
                raise PakValidationError(f"Each file entry must be a (pak_path, fs_path) tuple, got: {item!r}")

            raw_name, raw_fs_path = item
            pak_name = validate_pak_path(raw_name)
            fs_path = Path(raw_fs_path)

            if fs_path.resolve() == resolved_output:
                raise PakValidationError(f"Refusing to package output PAK itself as input: {fs_path}")
            if pak_name in seen_names:
                raise PakValidationError(f"Duplicate PAK target path: {pak_name}")
            if not fs_path.exists():
                raise PakValidationError(f"Input file does not exist: {fs_path}")
            if not fs_path.is_file():
                raise PakValidationError(f"Input path is not a file: {fs_path}")

            size = validate_i32(fs_path.stat().st_size, f"entry[{pak_name}].size")
            validate_i32(offset, f"entry[{pak_name}].offset")
            encoded_name = pak_name.encode("ascii")
            padded_name = encoded_name + (b"\x00" * (PAK_NAME_MAX_BYTES - len(encoded_name)))

            entries.append(
                _PakBuildEntry(
                    name=pak_name,
                    encoded_name=padded_name,
                    source_path=fs_path,
                    offset=offset,
                    size=size,
                )
            )
            seen_names.add(pak_name)
            offset = validate_i32(offset + size, "next_file_offset")

        return entries

    def write(self, output_path: Path, files: list[tuple[str, Path]]) -> None:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        entries = self._build_entries(output_path, files)

        dir_offset = entries[-1].offset + entries[-1].size if entries else PAK_HEADER_STRUCT.size
        dir_length = len(entries) * PAK_DIRECTORY_ENTRY_SIZE
        validate_i32(dir_offset, "dir_offset")
        validate_i32(dir_length, "dir_length")

        temp_name: str | None = None
        current_section = "header"
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb",
                suffix=".tmp",
                prefix=f"{output_path.stem}.",
                dir=output_path.parent,
                delete=False,
            ) as temp_file:
                temp_name = temp_file.name
                try:
                    temp_file.write(PAK_HEADER_STRUCT.pack(self.HEADER, dir_offset, dir_length))
                    for entry in entries:
                        current_section = f"data:{entry.name}"
                        data = entry.source_path.read_bytes()
                        if len(data) != entry.size:
                            raise PakBuildError(
                                f"Size changed while reading {entry.source_path}: "
                                f"expected={entry.size}, actual={len(data)}"
                            )
                        temp_file.write(data)

                    for entry in entries:
                        current_section = f"directory:{entry.name}"
                        temp_file.write(
                            PAK_DIRECTORY_ENTRY_STRUCT.pack(entry.encoded_name, entry.offset, entry.size)
                        )
                except struct.error as exc:
                    raise PakBuildError(f"Failed to pack PAK structures at {current_section}: {exc}") from exc

            Path(temp_name).replace(output_path)
        except OSError as exc:
            if temp_name:
                Path(temp_name).unlink(missing_ok=True)
            raise PakBuildError(f"Failed to write PAK '{output_path}': {exc}") from exc
        except PakError:
            if temp_name:
                Path(temp_name).unlink(missing_ok=True)
            raise
