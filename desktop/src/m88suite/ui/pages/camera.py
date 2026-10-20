"""Camera: video ao vivo, qualidade e webcam virtual."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtWidgets import (QCheckBox, QComboBox, QFormLayout, QHBoxLayout, QLabel, QPushButton,
                               QSizePolicy, QVBoxLayout, QWidget)

from ...core.device import StreamState, Telemetry
from ...core.stock.video import StreamConfig
from .. import icons, theme
from ..video import VirtualWebcam
from ..widgets import Pill, notice, page_header

# (rotulo, codec, transporte). H.264/UDP foi o melhor modo medido no firmware de fabrica.
MODES = [
    ("Fluido — H.264 / UDP (recomendado)", "h264", "udp"),
    ("Estável — H.264 / TCP", "h264", "tcp"),
    ("Fotos em sequência — JPEG / UDP", "jpeg", "udp"),
]
# 864x480 e o pedido que funciona; o firmware de fabrica entrega 640x480.
RESOLUTIONS = [("640 × 480 (máximo do firmware de fábrica)", 864, 480)]


class CameraPage(QWidget):
    def __init__(self, manager, decoder):
        super().__init__()
        self.manager, self.decoder = manager, decoder
        self.webcam: VirtualWebcam | None = None

        self.video = QLabel("Vídeo desligado")
        self.video.setObjectName("video")
        self.video.setAlignment(Qt.AlignCenter)
        self.video.setMinimumSize(480, 360)
        self.video.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)

        self.mode = QComboBox()
        for label, *_ in MODES:
            self.mode.addItem(label)
        self.resolution = QComboBox()
        for label, *_ in RESOLUTIONS:
            self.resolution.addItem(label)
        self.webcam_box = QCheckBox("Usar como webcam (OBS Virtual Camera)")
        self.webcam_box.toggled.connect(self._toggle_webcam)

        self.btn = QPushButton(icons.icon("play", "white"), "  Iniciar vídeo")
        self.btn.setObjectName("primary")
        self.btn.clicked.connect(self._toggle_stream)
        self.state = Pill("Desligado")
        self.stats = QLabel("")
        self.stats.setObjectName("subtitle")

        form = QFormLayout()
        form.addRow("Modo", self.mode)
        form.addRow("Resolução", self.resolution)
        form.addRow("", self.webcam_box)
        bar = QHBoxLayout()
        bar.addWidget(self.btn)
        bar.addWidget(self.state)
        bar.addWidget(self.stats, 1)

        side = QVBoxLayout()
        side.addLayout(form)
        side.addWidget(notice("Fique a até ~3 m do PC. Se o vídeo congelar, o app reinicia o óculos e "
                              "retoma sozinho (até 3 tentativas). Com o cabo USB conectado a câmera "
                              "não transmite — carregue numa tomada."))
        side.addStretch(1)

        body = QHBoxLayout()
        body.addWidget(self.video, 3)
        body.addLayout(side, 1)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)
        lay.addWidget(page_header("Câmera", "Vídeo ao vivo do óculos, no app ou como webcam"))
        lay.addLayout(bar)
        lay.addLayout(body, 1)

        decoder.image.connect(self._show)

    def _config(self) -> StreamConfig:
        _, codec, transport = MODES[self.mode.currentIndex()]
        _, w, h = RESOLUTIONS[self.resolution.currentIndex()]
        return StreamConfig(codec=codec, width=w, height=h, transport=transport)

    def _toggle_stream(self):
        if self.manager.telemetry.stream == StreamState.OFF:
            self.manager.start_stream(self._config())
        else:
            self.manager.stop_stream()

    def _toggle_webcam(self, on: bool):
        if on:
            try:
                self.webcam = VirtualWebcam()
                self.decoder.webcam = self.webcam
            except Exception as e:
                self.webcam_box.setChecked(False)
                self.stats.setText(f"Webcam virtual indisponível: {e}. Instale o OBS Studio.")
        else:
            self.decoder.webcam = None
            if self.webcam:
                self.webcam.close()
                self.webcam = None

    def _show(self, img: QImage):
        pm = QPixmap.fromImage(img).scaled(self.video.size(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
        self.video.setPixmap(pm)

    def update_telemetry(self, t: Telemetry):
        live = t.stream != StreamState.OFF
        self.btn.setText("  Parar vídeo" if live else "  Iniciar vídeo")
        self.btn.setIcon(icons.icon("stop" if live else "play", "white"))
        self.mode.setEnabled(not live)
        self.resolution.setEnabled(not live)
        color = {StreamState.LIVE: theme.OK, StreamState.OFF: theme.MUTED}.get(t.stream, theme.WARN)
        self.state.set(t.stream.value, color)
        if t.stream == StreamState.LIVE:
            self.stats.setText(f"{t.fps:.1f} fps · {t.kbps:.0f} kbit/s · descartados {t.dropped}")
        elif t.stream == StreamState.RECOVERING:
            self.stats.setText(f"Recuperando… tentativa {t.recoveries}")
        elif not live:
            self.stats.setText("")
            self.video.setText("Vídeo desligado")
