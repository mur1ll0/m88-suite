"""Janela principal: menu lateral + paginas + barra de estado."""
from __future__ import annotations

from PySide6.QtCore import QSettings, QSize, Qt
from PySide6.QtWidgets import (QHBoxLayout, QLabel, QListWidget, QListWidgetItem, QMainWindow,
                               QStackedWidget, QStatusBar, QVBoxLayout, QWidget)

from ..core.device import LinkState, StreamState, Telemetry
from ..core.manager import DEFAULT_ADDRESS, DeviceManager
from . import icons, theme
from .bridge import DeviceBridge
from .pages.camera import CameraPage
from .pages.dashboard import LINK_COLORS, DashboardPage
from .pages.info_pages import audio_page, buttons_page, firmware_page
from .pages.media import MediaPage
from .pages.settings import SettingsPage
from .video import VideoDecoder
from .widgets import Pill


class MainWindow(QMainWindow):
    def __init__(self, manager: DeviceManager | None = None):
        super().__init__()
        self.setWindowTitle("M88 Suite")
        self.setWindowIcon(icons.icon("glasses", theme.ACCENT, 64))
        self.resize(1280, 820)
        self.settings = QSettings("M88Suite", "M88Suite")

        self.bridge = DeviceBridge()
        address = self.settings.value("device/address", DEFAULT_ADDRESS)
        self.manager = manager or DeviceManager(self.bridge.listener(), address)
        self.decoder = VideoDecoder()
        self._last_link = LinkState.DISCONNECTED

        self.dashboard = DashboardPage(self.manager)
        self.camera = CameraPage(self.manager, self.decoder)
        self.media = MediaPage(self.manager, self.settings)
        pages = [
            ("Painel", "dashboard", self.dashboard),
            ("Câmera", "camera", self.camera),
            ("Fotos e vídeos", "media", self.media),
            ("Áudio", "audio", audio_page()),
            ("Botões", "buttons", buttons_page()),
            ("Firmware", "firmware", firmware_page()),
            ("Configurações", "settings", SettingsPage(self.manager, self.settings)),
        ]
        self.stack = QStackedWidget()
        self.nav = QListWidget()
        self.nav.setObjectName("nav")
        self.nav.setIconSize(QSize(22, 22))
        self.nav.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        for label, icon_name, page in pages:
            self.nav.addItem(QListWidgetItem(icons.icon(icon_name, theme.TEXT), f"  {label}"))
            self.stack.addWidget(page)
        self.nav.currentRowChanged.connect(self.stack.setCurrentIndex)
        self.nav.setCurrentRow(0)

        brand = QLabel("M88 Suite")
        brand.setObjectName("brand")
        sidebar = QWidget()
        sidebar.setObjectName("sidebar")
        sidebar.setFixedWidth(240)
        side = QVBoxLayout(sidebar)
        side.setContentsMargins(0, 0, 0, 12)
        side.addWidget(brand)
        side.addWidget(self.nav, 1)

        root = QWidget()
        root.setObjectName("root")
        body = QHBoxLayout(root)
        body.setContentsMargins(0, 0, 0, 0)
        body.setSpacing(0)
        body.addWidget(sidebar)
        body.addWidget(self.stack, 1)
        self.setCentralWidget(root)

        self.link_pill = Pill("Desconectado", theme.BAD)
        self.battery_label = QLabel("")
        status = QStatusBar()
        status.addPermanentWidget(self.battery_label)
        status.addPermanentWidget(self.link_pill)
        self.setStatusBar(status)

        self.bridge.telemetry.connect(self._on_telemetry)
        self.bridge.frame.connect(self.decoder.submit)
        self.bridge.log.connect(self.dashboard.append_log)
        self.bridge.log.connect(lambda line: self.statusBar().showMessage(line, 6000))

        if self.settings.value("device/autoconnect", True, type=bool) and manager is None:
            self.manager.connect()

    def _on_telemetry(self, t: Telemetry):
        self.dashboard.update_telemetry(t)
        self.camera.update_telemetry(t)
        self.link_pill.set(t.link.value, LINK_COLORS[t.link])
        self.battery_label.setText(f"Bateria {t.battery}%   " if t.battery is not None else "")
        became_connected = t.link == LinkState.CONNECTED and self._last_link != LinkState.CONNECTED
        self._last_link = t.link
        if became_connected and self.media.auto.isChecked() and t.stream == StreamState.OFF:
            self.media.sync()

    def closeEvent(self, event):
        self.camera._toggle_webcam(False)
        self.manager.shutdown()
        super().closeEvent(event)
