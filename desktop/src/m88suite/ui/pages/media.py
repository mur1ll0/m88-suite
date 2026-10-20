"""Midia: copia as fotos e videos do cartao do oculos para uma pasta do PC."""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtWidgets import (QCheckBox, QFileDialog, QHBoxLayout, QLabel, QListWidget, QListWidgetItem,
                               QPushButton, QVBoxLayout, QWidget)

from .. import icons
from ..widgets import page_header

DEFAULT_DIR = Path.home() / "Pictures" / "M88"
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".bmp"}


class MediaPage(QWidget):
    status_text = Signal(str)
    sync_done = Signal(str)  # mensagem de erro, ou "" em caso de sucesso

    def __init__(self, manager, settings):
        super().__init__()
        self.manager, self.settings = manager, settings
        self.folder = Path(settings.value("media/dir", str(DEFAULT_DIR)))
        self.folder.mkdir(parents=True, exist_ok=True)

        sync = QPushButton(icons.icon("sync", "white"), "  Sincronizar agora")
        sync.setObjectName("primary")
        sync.clicked.connect(self.sync)
        open_dir = QPushButton(icons.icon("folder"), "  Abrir pasta")
        open_dir.clicked.connect(lambda: os.startfile(self.folder))
        change = QPushButton("Trocar pasta…")
        change.clicked.connect(self._change_folder)
        self.sync_button = sync

        self.auto = QCheckBox("Sincronizar automaticamente ao conectar")
        self.auto.setChecked(settings.value("media/auto", True, type=bool))
        self.auto.toggled.connect(lambda on: settings.setValue("media/auto", on))

        self.status = QLabel()
        self.status.setObjectName("subtitle")
        self.status_text.connect(self.status.setText)
        self.sync_done.connect(self._on_sync_done)

        self.gallery = QListWidget()
        self.gallery.setObjectName("files")
        self.gallery.setViewMode(QListWidget.IconMode)
        self.gallery.setIconSize(QSize(176, 132))
        self.gallery.setResizeMode(QListWidget.Adjust)
        self.gallery.setSpacing(10)
        self.gallery.itemDoubleClicked.connect(lambda item: os.startfile(item.data(Qt.UserRole)))

        row = QHBoxLayout()
        row.addWidget(sync)
        row.addWidget(open_dir)
        row.addWidget(change)
        row.addStretch(1)
        row.addWidget(self.auto)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(14)
        lay.addWidget(page_header("Fotos e vídeos", "Cópia do cartão do óculos para o PC (somente arquivos novos)"))
        lay.addLayout(row)
        lay.addWidget(self.status)
        lay.addWidget(self.gallery, 1)
        self.refresh_gallery()

    def _change_folder(self):
        chosen = QFileDialog.getExistingDirectory(self, "Pasta de destino", str(self.folder))
        if chosen:
            self.folder = Path(chosen)
            self.settings.setValue("media/dir", chosen)
            self.refresh_gallery()

    def sync(self):
        self.sync_button.setEnabled(False)
        self.status_text.emit("Conectando ao óculos…")
        future = self.manager.sync_media(self.folder, self.status_text.emit)
        future.add_done_callback(self._sync_finished)

    def _sync_finished(self, future):
        # roda na thread do gerenciador: so emite o sinal, a UI reage na propria thread
        error = future.exception()
        self.sync_done.emit(str(error) if error else "")

    def _on_sync_done(self, error: str):
        if error:
            self.status.setText(f"Falha na sincronização: {error}")
        self.sync_button.setEnabled(True)
        self.refresh_gallery()

    def refresh_gallery(self):
        self.gallery.clear()
        files = sorted(self.folder.glob("*"), key=lambda p: p.stat().st_mtime, reverse=True)
        for path in files[:200]:
            if path.suffix.lower() in PHOTO_EXT:
                pm = QPixmap(str(path))
                item_icon = QIcon(pm.scaled(176, 132, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            elif path.suffix.lower() in {".mp4", ".avi", ".mov"}:
                item_icon = icons.icon("camera", size=96)
            else:
                continue
            item = QListWidgetItem(item_icon, path.name)
            item.setData(Qt.UserRole, str(path))
            self.gallery.addItem(item)
        if not self.status.text():
            self.status.setText(f"{self.gallery.count()} arquivo(s) em {self.folder}")
