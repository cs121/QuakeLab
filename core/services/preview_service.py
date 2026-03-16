from __future__ import annotations

from pathlib import Path

from ui.viewers.bsp_viewer import BspPreviewHandler
from ui.viewers.fallback_viewer import FallbackPreviewHandler
from ui.viewers.glsl_viewer import GlslPreviewHandler
from ui.viewers.image_viewer import ImagePreviewHandler
from ui.viewers.qc_viewer import QcPreviewHandler
from ui.viewers.text_viewer import TextPreviewHandler
from ui.viewers.wad_viewer import WadPreviewHandler
from ui.viewers.wav_viewer import WavPreviewHandler


class PreviewService:
    def __init__(self) -> None:
        self.handlers = [
            ImagePreviewHandler(),
            WavPreviewHandler(),
            GlslPreviewHandler(),
            QcPreviewHandler(),
            BspPreviewHandler(),
            WadPreviewHandler(),
            TextPreviewHandler(),
            FallbackPreviewHandler(),
        ]

    def handler_for(self, path: Path):
        for handler in self.handlers:
            if handler.can_handle(path):
                return handler
        return self.handlers[-1]
