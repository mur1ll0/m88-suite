"""Componentes visuais reutilizaveis."""
from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QFrame, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from . import icons, theme


class Card(QFrame):
    """Cartao de estado: icone + titulo + valor grande + detalhe."""

    def __init__(self, icon_name: str, title: str, parent: QWidget | None = None):
        super().__init__(parent)
        self.setObjectName("card")
        self.setMinimumSize(220, 130)
        self._icon_name = icon_name
        self._icon = QLabel()
        self._title = QLabel(title)
        self._title.setObjectName("cardTitle")
        self.value = QLabel("—")
        self.value.setObjectName("cardValue")
        self.detail = QLabel("")
        self.detail.setObjectName("subtitle")
        self.detail.setWordWrap(True)
        head = QHBoxLayout()
        head.addWidget(self._icon)
        head.addWidget(self._title, 1)
        lay = QVBoxLayout(self)
        lay.setContentsMargins(18, 16, 18, 16)
        lay.addLayout(head)
        lay.addWidget(self.value)
        lay.addWidget(self.detail)
        lay.addStretch(1)
        self.set_color(theme.MUTED)

    def set(self, value: str, detail: str = "", color: str | None = None):
        self.value.setText(value)
        self.detail.setText(detail)
        if color:
            self.set_color(color)

    def set_color(self, color: str):
        self._icon.setPixmap(icons.pixmap(self._icon_name, 26, color))


class Pill(QLabel):
    def __init__(self, text: str = "", color: str = theme.MUTED):
        super().__init__(text)
        self.setObjectName("pill")
        self.set(text, color)

    def set(self, text: str, color: str):
        self.setText(text)
        self.setStyleSheet(theme.pill_style(color))


def page_header(title: str, subtitle: str) -> QWidget:
    w = QWidget()
    lay = QVBoxLayout(w)
    lay.setContentsMargins(0, 0, 0, 8)
    t = QLabel(title)
    t.setObjectName("title")
    s = QLabel(subtitle)
    s.setObjectName("subtitle")
    s.setWordWrap(True)
    lay.addWidget(t)
    lay.addWidget(s)
    return w


def notice(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setWordWrap(True)
    lbl.setTextFormat(Qt.RichText)
    lbl.setStyleSheet(f"background: {theme.SURFACE}; border: 1px solid {theme.SURFACE_2};"
                      f"border-radius: 12px; padding: 14px; color: {theme.MUTED};")
    return lbl
