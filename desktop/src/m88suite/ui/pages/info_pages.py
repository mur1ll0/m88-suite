"""Paginas de Audio, Botoes e Firmware (recursos do sistema ou do firmware futuro)."""
from __future__ import annotations

import os

from PySide6.QtWidgets import QHBoxLayout, QLabel, QPushButton, QVBoxLayout, QWidget

from .. import icons
from ..widgets import notice, page_header


def _page(title: str, subtitle: str) -> tuple[QWidget, QVBoxLayout]:
    page = QWidget()
    lay = QVBoxLayout(page)
    lay.setContentsMargins(28, 24, 28, 24)
    lay.setSpacing(14)
    lay.addWidget(page_header(title, subtitle))
    return page, lay


def audio_page() -> QWidget:
    page, lay = _page("Áudio", "Use o óculos como fone de ouvido e microfone")
    lay.addWidget(notice(
        "O óculos já é um <b>headset Bluetooth</b> (A2DP para música, HFP para chamadas e microfone). "
        "Pareie uma vez pelo Windows e escolha <b>M88</b> como saída e entrada de áudio. "
        "Não é preciso driver nem este app ficar aberto."))
    row = QHBoxLayout()
    bt = QPushButton(icons.icon("bluetooth"), "  Configurações de Bluetooth")
    bt.clicked.connect(lambda: os.startfile("ms-settings:bluetooth"))
    snd = QPushButton(icons.icon("audio"), "  Configurações de som")
    snd.clicked.connect(lambda: os.startfile("ms-settings:sound"))
    row.addWidget(bt)
    row.addWidget(snd)
    row.addStretch(1)
    lay.addLayout(row)
    lay.addWidget(notice("Microfone pela rede Wi‑Fi ou USB fica para o firmware M88 Suite."))
    lay.addStretch(1)
    return page


# Eventos de botao encontrados nas mensagens do firmware V189. O fabricante nao documenta qual
# gesto dispara cada acao, entao a pagina mostra so o que foi observado.
STOCK_EVENTS = [
    ("BTN0 BSP_LONG_PRESS", "toque longo no botão 0"),
    ("BTN1 BSP_LONG_PRESS", "toque longo no botão 1"),
    ("BTN1 BSP_TRIPLE_CLICK", "toque triplo no botão 1"),
    ("BTN Start / stop recording", "iniciar / parar gravação"),
    ("BTN Shutdown system", "desligar"),
    ("BTN factory restore", "restauração de fábrica (gesto não identificado — cuidado)"),
]


def buttons_page() -> QWidget:
    page, lay = _page("Botões", "Atalhos dos botões do óculos")
    lay.addWidget(notice(
        "O firmware de fábrica não permite mudar os atalhos. A configuração de gestos "
        "(ex.: 1 toque frontal = foto, 2 toques traseiros = gravar vídeo) chega com o firmware M88 Suite."))
    lay.addWidget(QLabel("Eventos encontrados no firmware de fábrica:"))
    for gesture, action in STOCK_EVENTS:
        row = QHBoxLayout()
        g = QLabel(gesture)
        a = QLabel(action)
        a.setObjectName("subtitle")
        row.addWidget(g, 1)
        row.addWidget(a, 2)
        lay.addLayout(row)
    lay.addStretch(1)
    return page


def firmware_page() -> QWidget:
    page, lay = _page("Firmware", "Versão instalada e atualizações")
    for label, value in (("Instalada", "0039000B V191 (fábrica)"),
                         ("Disponível no servidor do fabricante", "V189 (mais antiga)"),
                         ("Chip", "Beken BK7258QN6868 · placa JY_5BG_V4")):
        row = QHBoxLayout()
        row.addWidget(QLabel(label), 1)
        v = QLabel(value)
        v.setObjectName("subtitle")
        row.addWidget(v, 2)
        lay.addLayout(row)
    lay.addWidget(notice(
        "A atualização pelo Bluetooth existe no óculos, mas fica desativada neste app até haver uma "
        "cópia de segurança do firmware atual (requer conexão serial). Detalhes em "
        "<b>docs/FIRMWARE_UPDATE.md</b>."))
    update = QPushButton(icons.icon("firmware"), "  Atualizar firmware")
    update.setEnabled(False)
    lay.addWidget(update)
    lay.addStretch(1)
    return page
