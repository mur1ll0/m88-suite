"""Midia: o que esta no oculos, para onde baixar e o que ja foi baixado."""
from __future__ import annotations

import os
from pathlib import Path

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtGui import QColor, QIcon, QPixmap
from PySide6.QtWidgets import (QAbstractItemView, QCheckBox, QDialog, QDialogButtonBox, QFileDialog, QHBoxLayout,
                               QHeaderView, QLabel, QListWidget, QListWidgetItem, QMessageBox, QProgressBar,
                               QPushButton, QTabWidget, QTreeWidget, QTreeWidgetItem, QVBoxLayout, QWidget)

from ...core.media import RemoteMedia, local_files, pretty_name, pretty_size
from .. import icons, theme
from ..widgets import page_header

DEFAULT_DIR = Path.home() / "Pictures" / "M88"
PHOTO_EXT = {".jpg", ".jpeg", ".png", ".bmp"}


class MediaPage(QWidget):
    # Resultados chegam da thread do gerenciador; os sinais entregam na thread da UI.
    remote_loaded = Signal(object)  # list[RemoteMedia]
    status_text = Signal(str)
    operation_done = Signal(str)  # mensagem final ("" = sem mensagem)
    preview_ready = Signal(object, bytes)

    def __init__(self, manager, settings):
        super().__init__()
        self.manager, self.settings = manager, settings
        self.folder = Path(settings.value("media/dir", str(DEFAULT_DIR)))
        self.remote: list[RemoteMedia] = []
        self.busy = False
        self._auto_pending = False

        # destino + opcoes
        self.folder_label = QLabel()
        self.folder_label.setObjectName("subtitle")
        change = QPushButton(icons.icon("folder"), "  Trocar pasta…")
        change.clicked.connect(self._change_folder)
        open_dir = QPushButton("Abrir pasta")
        open_dir.clicked.connect(lambda: os.startfile(self.folder))
        self.delete_after = QCheckBox("Apagar do óculos depois de baixar")
        self.delete_after.setToolTip("Só apaga depois de conferir que o arquivo baixado tem o mesmo tamanho do original.")
        self.delete_after.setChecked(settings.value("media/delete_after", False, type=bool))
        self.delete_after.toggled.connect(lambda on: settings.setValue("media/delete_after", on))
        self.auto = QCheckBox("Baixar os novos automaticamente ao conectar")
        self.auto.setChecked(settings.value("media/auto", True, type=bool))
        self.auto.toggled.connect(lambda on: settings.setValue("media/auto", on))

        dest_row = QHBoxLayout()
        dest_row.addWidget(QLabel("Salvar em:"))
        dest_row.addWidget(self.folder_label, 1)
        dest_row.addWidget(change)
        dest_row.addWidget(open_dir)
        opts = QHBoxLayout()
        opts.addWidget(self.delete_after)
        opts.addWidget(self.auto)
        opts.addStretch(1)

        self.status = QLabel()
        self.status.setObjectName("subtitle")
        self.progress = QProgressBar()
        self.progress.setRange(0, 0)
        self.progress.setVisible(False)

        self.tabs = QTabWidget()
        self.tabs.addTab(self._build_remote_tab(), "No óculos")
        self.tabs.addTab(self._build_local_tab(), "Baixadas")

        lay = QVBoxLayout(self)
        lay.setContentsMargins(28, 24, 28, 24)
        lay.setSpacing(12)
        lay.addWidget(page_header("Fotos e vídeos", "O que está no óculos e o que já está no PC"))
        lay.addLayout(dest_row)
        lay.addLayout(opts)
        lay.addWidget(self.progress)
        lay.addWidget(self.status)
        lay.addWidget(self.tabs, 1)

        self.remote_loaded.connect(self._show_remote)
        self.status_text.connect(self.status.setText)
        self.operation_done.connect(self._finish)
        self.preview_ready.connect(self._show_preview)
        self._update_folder_label()
        self.refresh_local()

    # ------------------------------------------------------------------ construcao
    def _build_remote_tab(self) -> QWidget:
        self.tree = QTreeWidget()
        self.tree.setHeaderLabels(["Data e hora", "Tipo", "Tamanho", ""])
        self.tree.setRootIsDecorated(False)
        self.tree.setAlternatingRowColors(True)
        self.tree.setSelectionMode(QAbstractItemView.NoSelection)
        self.tree.header().setSectionResizeMode(0, QHeaderView.Stretch)
        self.tree.itemDoubleClicked.connect(self._open_remote)
        self.tree.itemChanged.connect(lambda *_: self._update_buttons())

        self.btn_refresh = QPushButton(icons.icon("sync"), "  Atualizar")
        self.btn_refresh.clicked.connect(self.refresh_remote)
        self.btn_all = QPushButton("Selecionar tudo")
        self.btn_all.clicked.connect(self._toggle_all)
        self.btn_download = QPushButton(icons.icon("media", "white"), "  Baixar novos")
        self.btn_download.setObjectName("primary")
        self.btn_download.clicked.connect(self._download_clicked)
        self.btn_delete = QPushButton("Apagar do óculos")
        self.btn_delete.setObjectName("danger")
        self.btn_delete.clicked.connect(self._delete_clicked)

        row = QHBoxLayout()
        for b in (self.btn_download, self.btn_delete, self.btn_refresh, self.btn_all):
            row.addWidget(b)
        row.addStretch(1)
        hint = QLabel("Dê dois cliques numa foto para pré-visualizar.")
        hint.setObjectName("subtitle")

        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addLayout(row)
        lay.addWidget(self.tree, 1)
        lay.addWidget(hint)
        return w

    def _build_local_tab(self) -> QWidget:
        self.gallery = QListWidget()
        self.gallery.setObjectName("files")
        self.gallery.setViewMode(QListWidget.IconMode)
        self.gallery.setIconSize(QSize(176, 132))
        self.gallery.setResizeMode(QListWidget.Adjust)
        self.gallery.setSpacing(10)
        self.gallery.itemDoubleClicked.connect(lambda item: os.startfile(item.data(Qt.UserRole)))
        w = QWidget()
        lay = QVBoxLayout(w)
        lay.addWidget(self.gallery)
        return w

    # ------------------------------------------------------------------ estado
    def _update_folder_label(self):
        self.folder_label.setText(str(self.folder))

    def _set_busy(self, busy: bool, text: str = ""):
        self.busy = busy
        self.progress.setVisible(busy)
        if text:
            self.status.setText(text)
        self._update_buttons()

    def _checked(self) -> list[RemoteMedia]:
        out = []
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if item.checkState(0) == Qt.Checked:
                out.append(item.data(0, Qt.UserRole))
        return out

    def _local_names(self) -> set[str]:
        return {p.name for p in local_files(self.folder)}

    def _update_buttons(self):
        checked = self._checked()
        self.btn_download.setText(f"  Baixar ({len(checked)})" if checked else "  Baixar novos")
        self.btn_download.setEnabled(not self.busy and bool(self.remote))
        self.btn_delete.setEnabled(not self.busy and bool(checked))
        self.btn_refresh.setEnabled(not self.busy)

    # ------------------------------------------------------------------ acoes
    def _change_folder(self):
        chosen = QFileDialog.getExistingDirectory(self, "Pasta de destino", str(self.folder))
        if chosen:
            self.folder = Path(chosen)
            self.settings.setValue("media/dir", chosen)
            self._update_folder_label()
            self.refresh_local()
            self._show_remote(self.remote)

    def _track(self, future, done_message):
        """Liga um Future do gerenciador ao fim da operacao na UI."""
        def finished(f):
            err = f.exception()
            if err:
                self.operation_done.emit(f"Falha: {err}")
                return
            result = f.result()
            if isinstance(result, list):
                self.remote_loaded.emit(result)
            self.operation_done.emit(done_message(result))
        future.add_done_callback(finished)

    def refresh_remote(self):
        if self.busy:
            return
        self._set_busy(True, "Lendo o cartão do óculos…")
        self._track(self.manager.list_remote(), lambda r: f"{len(r)} arquivo(s) no óculos")

    def _download(self, items: list[RemoteMedia]):
        if not items or self.busy:
            return
        delete = self.delete_after.isChecked()
        self._set_busy(True, "Preparando download…")

        def summary(r):
            parts = [f"Baixado(s): {r.downloaded}"]
            if delete:
                parts.append(f"{r.deleted} apagado(s) do óculos")
            if r.failed:
                parts.append(f"{r.failed} falha(s) — continuam no óculos")
            return ", ".join(parts)
        future = self.manager.download(items, self.folder, delete, self.status_text.emit)
        future.add_done_callback(lambda f: None if f.exception() else self.manager.list_remote().add_done_callback(
            lambda g: None if g.exception() else self.remote_loaded.emit(g.result())))
        self._track(future, summary)

    def _download_clicked(self):
        items = self._checked() or [m for m in self.remote if m.name not in self._local_names()]
        if not items:
            self.status.setText("Nada novo para baixar.")
            return
        self._download(items)

    def _delete_clicked(self):
        items = self._checked()
        local = self._local_names()
        missing = sum(1 for m in items if m.name not in local)
        warn = f"\n\n{missing} deles ainda não foram baixados e serão perdidos." if missing else ""
        answer = QMessageBox.question(self, "Apagar do óculos",
                                      f"Apagar {len(items)} arquivo(s) do cartão do óculos?{warn}")
        if answer != QMessageBox.Yes:
            return
        self._set_busy(True, "Apagando do óculos…")
        future = self.manager.delete_remote(items)
        future.add_done_callback(lambda f: None if f.exception() else self.manager.list_remote().add_done_callback(
            lambda g: None if g.exception() else self.remote_loaded.emit(g.result())))
        self._track(future, lambda n: f"{n} arquivo(s) apagado(s) do óculos")

    def _open_remote(self, tree_item: QTreeWidgetItem, _column: int):
        item: RemoteMedia = tree_item.data(0, Qt.UserRole)
        if item.is_video or self.busy:
            return
        self._set_busy(True, f"Abrindo {pretty_name(item.name)}…")
        future = self.manager.preview(item)

        def finished(f):
            if f.exception():
                self.operation_done.emit(f"Falha: {f.exception()}")
            else:
                self.operation_done.emit("")
                self.preview_ready.emit(item, f.result())
        future.add_done_callback(finished)

    def auto_sync(self):
        """Chamado ao conectar: lista o oculos e, se a opcao estiver ligada, baixa o que for novo."""
        if self.busy:
            return
        self._set_busy(True, "Procurando arquivos novos no óculos…")
        future = self.manager.list_remote()

        def finished(f):
            if f.exception():
                self.operation_done.emit(f"Falha: {f.exception()}")
                return
            self.remote_loaded.emit(f.result())
            self.operation_done.emit("")
        future.add_done_callback(finished)
        self._auto_pending = self.auto.isChecked()

    # ------------------------------------------------------------------ resultados (thread da UI)
    def _finish(self, message: str):
        self._set_busy(False, message)
        self.refresh_local()
        if self._auto_pending:
            self._auto_pending = False
            new = [m for m in self.remote if m.name not in self._local_names()]
            if new:
                self._download(new)
            elif not message:
                self.status.setText("Nada novo no óculos.")

    def _show_remote(self, files: list[RemoteMedia]):
        self.remote = files
        local = self._local_names()
        self.tree.blockSignals(True)
        self.tree.clear()
        for m in files:
            row = QTreeWidgetItem([pretty_name(m.name), "Vídeo" if m.is_video else "Foto", pretty_size(m.size),
                                   "✓ baixado" if m.name in local else ""])
            row.setData(0, Qt.UserRole, m)
            row.setFlags(row.flags() | Qt.ItemIsUserCheckable)
            row.setCheckState(0, Qt.Unchecked)
            row.setIcon(0, icons.icon("camera" if m.is_video else "media", theme.ACCENT))
            if m.name in local:
                row.setForeground(3, QColor(theme.OK))
            self.tree.addTopLevelItem(row)
        self.tree.blockSignals(False)
        self.tabs.setTabText(0, f"No óculos ({len(files)})")
        self._update_buttons()

    def _toggle_all(self):
        count = self.tree.topLevelItemCount()
        target = Qt.Unchecked if len(self._checked()) == count else Qt.Checked
        self.tree.blockSignals(True)
        for i in range(count):
            self.tree.topLevelItem(i).setCheckState(0, target)
        self.tree.blockSignals(False)
        self._update_buttons()

    def _show_preview(self, item: RemoteMedia, data: bytes):
        dlg = QDialog(self)
        dlg.setWindowTitle(pretty_name(item.name))
        pm = QPixmap()
        pm.loadFromData(data)
        img = QLabel()
        img.setPixmap(pm.scaled(900, 640, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        buttons = QDialogButtonBox()
        buttons.addButton("Baixar", QDialogButtonBox.AcceptRole)
        buttons.addButton("Fechar", QDialogButtonBox.RejectRole)
        buttons.accepted.connect(dlg.accept)
        buttons.rejected.connect(dlg.reject)
        lay = QVBoxLayout(dlg)
        lay.addWidget(img)
        lay.addWidget(buttons)
        if dlg.exec() == QDialog.Accepted:
            self._download([item])

    def refresh_local(self):
        self.gallery.clear()
        files = local_files(self.folder)
        for path in files[:300]:
            if path.suffix.lower() in PHOTO_EXT:
                icon = QIcon(QPixmap(str(path)).scaled(176, 132, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                icon = icons.icon("camera", size=96)
            item = QListWidgetItem(icon, pretty_name(path.name))
            item.setData(Qt.UserRole, str(path))
            self.gallery.addItem(item)
        self.tabs.setTabText(1, f"Baixadas ({len(files)})")
