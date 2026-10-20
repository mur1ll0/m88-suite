"""Configuracoes persistentes (QSettings)."""
from __future__ import annotations

from PySide6.QtWidgets import QCheckBox, QFormLayout, QLabel, QLineEdit, QPushButton, QVBoxLayout, QWidget

from ...core import wifi
from ...core.manager import DEFAULT_ADDRESS
from ..widgets import notice, page_header


class SettingsPage(QWidget):
    def __init__(self, manager, settings):
        super().__init__()
        self.manager, self.settings = manager, settings
        self.address = QLineEdit(settings.value("device/address", DEFAULT_ADDRESS))
        self.autoconnect = QCheckBox("Conectar ao abrir o app")
        self.autoconnect.setChecked(settings.value("device/autoconnect", True, type=bool))
        save = QPushButton("Salvar")
        save.setObjectName("primary")
        save.clicked.connect(self._save)
        self.saved = QLabel("")
        self.saved.setObjectName("subtitle")

        form = QFormLayout()
        form.addRow("Endereço Bluetooth", self.address)
        form.addRow("Rede Wi‑Fi do óculos", QLabel(f"{wifi.SSID} (senha {wifi.PASSWORD})"))
        form.addRow("", self.autoconnect)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)
        lay.addWidget(page_header("Configurações", "Preferências do app"))
        lay.addLayout(form)
        lay.addWidget(save)
        lay.addWidget(self.saved)
        lay.addWidget(notice("Dica: um adaptador Wi‑Fi USB separado só para a rede do óculos reduz "
                             "travamentos (o rádio do PC divide Wi‑Fi e Bluetooth). Ver docs/HARDWARE.md."))
        lay.addStretch(1)

    def _save(self):
        self.settings.setValue("device/address", self.address.text().strip())
        self.settings.setValue("device/autoconnect", self.autoconnect.isChecked())
        self.manager.address = self.address.text().strip()
        self.saved.setText("Salvo. O endereço vale na próxima conexão.")
