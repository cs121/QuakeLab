from __future__ import annotations

import json
import os
import platform
import tarfile
import threading
import urllib.request
import zipfile
from collections.abc import Callable
from pathlib import Path

from core.services.log_service import LogService
from core.services.settings_service import SettingsService

# GitHub API endpoints for latest releases
TOOL_REGISTRY: dict[str, dict] = {
    "ericw-tools": {
        "api_url": "https://api.github.com/repos/ericwa/ericw-tools/releases/latest",
        "description": "Quake BSP/VIS/LIGHT compiler suite by Eric Wasylishen",
        "linux_pattern": "Linux",
        "windows_pattern": "Windows",
        "macos_pattern": "macOS",
        "executables": ["qbsp", "vis", "light"],
        "settings_map": {
            "qbsp": "qbsp_executable",
            "vis": "vis_executable",
            "light": "light_executable",
        },
    },
    "trenchbroom": {
        "api_url": "https://api.github.com/repos/TrenchBroom/TrenchBroom/releases/latest",
        "description": "TrenchBroom map editor",
        "linux_pattern": "Linux",
        "windows_pattern": "Win64",
        "macos_pattern": "macOS",
        "executables": ["TrenchBroom"],
        "settings_map": {
            "TrenchBroom": "trenchbroom_exe",
        },
    },
}


class DownloadProgress:
    """Carries progress information for a download operation."""

    def __init__(self, tool_name: str) -> None:
        self.tool_name = tool_name
        self.total: int = 0
        self.downloaded: int = 0
        self.message: str = ""
        self.done: bool = False
        self.ok: bool = False
        self.error: str = ""
        self.installed_paths: dict[str, str] = {}  # exe_name → absolute path


class ToolDownloadService:
    def __init__(self, settings: SettingsService, logs: LogService) -> None:
        self.settings = settings
        self.logs = logs

    def toolchain_dir(self) -> Path:
        """Returns (and creates) the toolchain directory inside the project root."""
        d = self.settings.project_root / "toolchain"
        d.mkdir(parents=True, exist_ok=True)
        return d

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def available_tools(self) -> list[str]:
        return list(TOOL_REGISTRY.keys())

    def tool_description(self, tool_name: str) -> str:
        return TOOL_REGISTRY.get(tool_name, {}).get("description", "")

    def download_async(
        self,
        tool_name: str,
        on_progress: Callable[[DownloadProgress], None] | None = None,
        auto_configure: bool = True,
    ) -> DownloadProgress:
        """Start a background download. Returns a DownloadProgress object that is updated in place."""
        progress = DownloadProgress(tool_name)
        thread = threading.Thread(
            target=self._download_worker,
            args=(tool_name, progress, on_progress, auto_configure),
            daemon=True,
        )
        thread.start()
        return progress

    def install_from_archive(self, tool_name: str, archive_path: Path, auto_configure: bool = True) -> dict[str, str]:
        """Install a tool from a locally downloaded archive file. Returns dict of exe → path."""
        if tool_name not in TOOL_REGISTRY:
            raise ValueError(f"Unknown tool: {tool_name}")
        dest = self.toolchain_dir() / tool_name
        dest.mkdir(parents=True, exist_ok=True)
        installed = self._extract_archive(archive_path, dest)
        if auto_configure and installed:
            self._apply_settings(tool_name, installed)
        return installed

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _download_worker(
        self,
        tool_name: str,
        progress: DownloadProgress,
        on_progress: Callable[[DownloadProgress], None] | None,
        auto_configure: bool,
    ) -> None:
        def _emit(msg: str = "") -> None:
            if msg:
                progress.message = msg
            if on_progress:
                on_progress(progress)

        try:
            info = TOOL_REGISTRY[tool_name]
            _emit(f"Fetching release info for {tool_name}…")
            asset_url, asset_name = self._fetch_release_asset(info)
            _emit(f"Downloading {asset_name}…")

            dest_dir = self.toolchain_dir() / tool_name
            dest_dir.mkdir(parents=True, exist_ok=True)
            archive_path = dest_dir / asset_name

            self._download_file(asset_url, archive_path, progress, on_progress)

            _emit("Extracting…")
            installed = self._extract_archive(archive_path, dest_dir)

            if auto_configure and installed:
                _emit("Configuring settings…")
                self._apply_settings(tool_name, installed)

            progress.installed_paths = installed
            progress.ok = True
            progress.done = True
            _emit(f"Done. {len(installed)} executable(s) installed.")
            self.logs.write("INFO", "ToolDownload", f"{tool_name}: installed to {dest_dir}")
        except Exception as exc:  # noqa: BLE001
            progress.error = str(exc)
            progress.done = True
            _emit(f"Error: {exc}")
            self.logs.write("ERROR", "ToolDownload", f"{tool_name}: {exc}")

    def _fetch_release_asset(self, info: dict) -> tuple[str, str]:
        """Return (download_url, filename) for the appropriate platform asset."""
        req = urllib.request.Request(
            info["api_url"],
            headers={"User-Agent": "QuakeLab/1.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            release = json.loads(resp.read().decode())

        system = platform.system().lower()
        if system == "linux":
            pattern = info["linux_pattern"]
        elif system == "windows":
            pattern = info["windows_pattern"]
        elif system == "darwin":
            pattern = info["macos_pattern"]
        else:
            pattern = info["linux_pattern"]

        assets = release.get("assets", [])
        for asset in assets:
            name: str = asset["name"]
            if pattern.lower() in name.lower():
                return asset["browser_download_url"], name

        # Fallback: first asset
        if assets:
            first = assets[0]
            return first["browser_download_url"], first["name"]

        raise RuntimeError(f"No suitable release asset found for {platform.system()}")

    def _download_file(
        self,
        url: str,
        dest: Path,
        progress: DownloadProgress,
        on_progress: Callable[[DownloadProgress], None] | None,
    ) -> None:
        req = urllib.request.Request(url, headers={"User-Agent": "QuakeLab/1.0"})
        with urllib.request.urlopen(req, timeout=60) as resp:
            total = int(resp.headers.get("Content-Length", 0))
            progress.total = total
            chunk_size = 65536
            downloaded = 0
            with open(dest, "wb") as f:
                while True:
                    chunk = resp.read(chunk_size)
                    if not chunk:
                        break
                    f.write(chunk)
                    downloaded += len(chunk)
                    progress.downloaded = downloaded
                    if on_progress:
                        on_progress(progress)

    def _extract_archive(self, archive_path: Path, dest_dir: Path) -> dict[str, str]:
        """Extract archive and return dict mapping exe name → absolute path."""
        name = archive_path.name.lower()
        if name.endswith(".zip"):
            with zipfile.ZipFile(archive_path, "r") as zf:
                zf.extractall(dest_dir)
        elif name.endswith((".tar.gz", ".tgz", ".tar.bz2", ".tar.xz")):
            with tarfile.open(archive_path, "r:*") as tf:
                tf.extractall(dest_dir)
        else:
            # Maybe it's already an executable
            return {}

        # Find executables in extracted content
        installed: dict[str, str] = {}
        for fpath in dest_dir.rglob("*"):
            if fpath.is_file() and fpath != archive_path:
                stem = fpath.stem.lower()
                # Mark executable on Linux/macOS
                if platform.system() != "Windows":
                    os.chmod(fpath, fpath.stat().st_mode | 0o111)
                installed[stem] = str(fpath.resolve())
        return installed

    def _apply_settings(self, tool_name: str, installed: dict[str, str]) -> None:
        info = TOOL_REGISTRY[tool_name]
        settings_map = info.get("settings_map", {})
        for exe_name, settings_key in settings_map.items():
            exe_lower = exe_name.lower()
            # Try exact match first, then prefix match
            path = installed.get(exe_lower)
            if path is None:
                for stem, p in installed.items():
                    if stem.startswith(exe_lower):
                        path = p
                        break
            if path:
                self.settings.set(settings_key, path)
                self.logs.write("INFO", "ToolDownload", f"  Set {settings_key} = {path}")
