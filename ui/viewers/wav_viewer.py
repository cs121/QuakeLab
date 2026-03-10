from __future__ import annotations

import wave
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtMultimedia import QAudioOutput, QMediaPlayer
from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from ui.viewers.base import PreviewHandler


class WavPreviewHandler(PreviewHandler):
    exts = {".wav"}

    def can_handle(self, path: Path) -> bool:
        return path.suffix.lower() in self.exts

    def create_widget(self, path: Path) -> QWidget:
        root = QWidget()
        layout = QVBoxLayout(root)

        with wave.open(str(path), "rb") as wav:
            channels = wav.getnchannels()
            rate = wav.getframerate()
            frames = wav.getnframes()
            duration = frames / float(rate)

        info = QLabel(f"Channels: {channels} | Rate: {rate}Hz | Duration: {duration:.2f}s")
        layout.addWidget(info)

        row = QHBoxLayout()
        player = QMediaPlayer(root)
        audio = QAudioOutput(root)
        player.setAudioOutput(audio)
        player.setSource(QUrl.fromLocalFile(str(path.resolve())))

        play = QPushButton("Play")
        stop = QPushButton("Stop")
        play.clicked.connect(player.play)
        stop.clicked.connect(player.stop)
        row.addWidget(play)
        row.addWidget(stop)
        layout.addLayout(row)

        return root
