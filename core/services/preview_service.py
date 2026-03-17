from __future__ import annotations

from pathlib import Path

from ui.viewers.bsp_viewer import BspPreviewHandler
from ui.viewers.dem_viewer import DemPreviewHandler
from ui.viewers.fallback_viewer import FallbackPreviewHandler
from ui.viewers.glsl_viewer import GlslPreviewHandler
from ui.viewers.image_viewer import ImagePreviewHandler
from ui.viewers.lmp_viewer import LmpPreviewHandler
from ui.viewers.mdl_viewer import MdlPreviewHandler
from ui.viewers.spr_viewer import SprPreviewHandler
from ui.viewers.text_viewer import TextPreviewHandler
from ui.viewers.wad_viewer import WadPreviewHandler
from ui.viewers.wav_viewer import WavPreviewHandler


class PreviewService:
    def __init__(self, settings=None) -> None:
        self._settings = settings
        self.handlers = [
            ImagePreviewHandler(),
            WavPreviewHandler(),
            GlslPreviewHandler(),
            BspPreviewHandler(),
            LmpPreviewHandler(settings=settings),
            WadPreviewHandler(settings=settings),
            MdlPreviewHandler(settings=settings),
            SprPreviewHandler(settings=settings),
            DemPreviewHandler(),
            TextPreviewHandler(),
            FallbackPreviewHandler(),
        ]

    def handler_for(self, path: Path):
        for handler in self.handlers:
            if handler.can_handle(path):
                return handler
        return self.handlers[-1]
