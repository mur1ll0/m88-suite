"""Painel: estado do oculos em cartoes + acoes rapidas + atividade recente."""
from __future__ import annotations

from PySide6.QtWidgets import QGridLayout, QHBoxLayout, QPlainTextEdit, QPushButton, QVBoxLayout, QWidget

from ...core.device import LinkState, StreamState, Telemetry
from .. import icons, theme
from ..widgets import Card, notice, page_header

LINK_COLORS = {LinkState.CONNECTED: theme.OK, LinkState.CONNECTING: theme.WARN,
               LinkState.RECONNECTING: theme.WARN, LinkState.DISCONNECTED: theme.BAD}


class DashboardPage(QWidget):
    def __init__(self, manager):
        super().__init__()
        self.manager = manager
        self.cards = {
            "link": Card("bluetooth", "Bluetooth"),
            "battery": Card("battery", "Bateria"),
            "wifi": Card("wifi", "Wi-Fi"),
            "camera": Card("camera", "Câmera"),
            "media": Card("media", "Fotos e vídeos"),
            "system": Card("glasses", "Óculos"),
        }
        grid = QGridLayout()
        grid.setSpacing(14)
        for i, card in enumerate(self.cards.values()):
            grid.addWidget(card, i // 3, i % 3)

        self.btn_connect = QPushButton(icons.icon("bluetooth", "white"), "  Conectar")
        self.btn_connect.setObjectName("primary")
        self.btn_connect.clicked.connect(self._toggle_connect)
        self.btn_restart = QPushButton(icons.icon("power"), "  Reiniciar óculos")
        self.btn_restart.clicked.connect(lambda: self.manager.restart_device())
        actions = QHBoxLayout()
        actions.addWidget(self.btn_connect)
        actions.addWidget(self.btn_restart)
        actions.addStretch(1)

        self.activity = QPlainTextEdit()
        self.activity.setReadOnly(True)
        self.activity.setMaximumBlockCount(300)
        self.activity.setPlaceholderText("Atividade aparecerá aqui")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)
        lay.addWidget(page_header("Painel", "Estado do óculos M88 em tempo real"))
        lay.addLayout(actions)
        lay.addLayout(grid)
        lay.addWidget(notice("LED e lanterna não são informados pelo firmware de fábrica. "
                             "Esses indicadores chegam com o firmware M88 Suite."))
        lay.addWidget(self.activity, 1)
        self.update_telemetry(Telemetry())

    def _toggle_connect(self):
        if self.manager.telemetry.link == LinkState.DISCONNECTED:
            self.manager.connect()
        else:
            self.manager.disconnect()

    def append_log(self, line: str):
        self.activity.appendPlainText(line)

    def update_telemetry(self, t: Telemetry):
        c = self.cards
        c["link"].set(t.link.value, "Reconexão automática ativa" if t.link != LinkState.DISCONNECTED else "",
                      LINK_COLORS[t.link])
        self.btn_connect.setText("  Desconectar" if t.link != LinkState.DISCONNECTED else "  Conectar")
        if t.battery is None:
            c["battery"].set("—", "aguardando o óculos", theme.MUTED)
        else:
            color = theme.OK if t.battery > 40 else theme.WARN if t.battery > 15 else theme.BAD
            c["battery"].set(f"{t.battery}%", "", color)
        ap = {"on": "AP ligado", "client": "PC conectado"}.get(t.wifi_ap or "", "desligado")
        c["wifi"].set("Conectado" if t.wifi_pc else ap.capitalize(),
                      "Rede M88-522B" if t.wifi_pc else "liga sob demanda (vídeo e mídia)",
                      theme.OK if t.wifi_pc else theme.MUTED)
        live = t.stream == StreamState.LIVE
        c["camera"].set(t.stream.value, f"{t.fps:.1f} fps · {t.kbps:.0f} kbit/s" if live else "",
                        theme.OK if live else theme.WARN if t.stream != StreamState.OFF else theme.MUTED)
        c["media"].set("—" if t.media_count is None else str(t.media_count), "arquivos no cartão",
                       theme.ACCENT if t.media_count else theme.MUTED)
        flags = ", ".join(t.system_flags) or "em espera"
        c["system"].set("Online" if t.link == LinkState.CONNECTED else "—", flags,
                        theme.OK if t.link == LinkState.CONNECTED else theme.MUTED)
