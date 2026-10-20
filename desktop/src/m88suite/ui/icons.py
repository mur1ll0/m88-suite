"""Icones em SVG (traco simples, 24x24) desenhados para a M88 Suite."""
from PySide6.QtCore import QByteArray, Qt
from PySide6.QtGui import QIcon, QPainter, QPixmap
from PySide6.QtSvg import QSvgRenderer

_PATHS = {
    "dashboard": '<rect x="3" y="3" width="7" height="9" rx="2"/><rect x="14" y="3" width="7" height="5" rx="2"/>'
                 '<rect x="14" y="12" width="7" height="9" rx="2"/><rect x="3" y="16" width="7" height="5" rx="2"/>',
    "camera": '<path d="M4 7h3l2-3h6l2 3h3a1 1 0 0 1 1 1v11a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1V8a1 1 0 0 1 1-1z"/>'
              '<circle cx="12" cy="13" r="4"/>',
    "media": '<rect x="3" y="4" width="18" height="16" rx="2"/><circle cx="9" cy="10" r="2"/>'
             '<path d="M21 16l-5-5-9 9"/>',
    "audio": '<path d="M4 14v-2a8 8 0 0 1 16 0v2"/><rect x="3" y="14" width="4" height="6" rx="1.5"/>'
             '<rect x="17" y="14" width="4" height="6" rx="1.5"/>',
    "buttons": '<rect x="5" y="3" width="14" height="18" rx="7"/><path d="M12 7v4"/>',
    "firmware": '<rect x="6" y="6" width="12" height="12" rx="2"/><path d="M9 2v4M15 2v4M9 18v4M15 18v4'
                'M2 9h4M2 15h4M18 9h4M18 15h4"/>',
    "settings": '<circle cx="12" cy="12" r="3"/><path d="M12 2v3M12 19v3M2 12h3M19 12h3M5 5l2 2M17 17l2 2'
                'M5 19l2-2M17 7l2-2"/>',
    "battery": '<rect x="2" y="7" width="17" height="10" rx="2"/><path d="M22 11v2"/>',
    "bluetooth": '<path d="M7 7l10 10-5 4V3l5 4L7 17"/>',
    "wifi": '<path d="M2 9a15 15 0 0 1 20 0M5 13a10 10 0 0 1 14 0M8.5 16.5a5 5 0 0 1 7 0"/>'
            '<circle cx="12" cy="20" r="1"/>',
    "power": '<path d="M12 2v10"/><path d="M5.6 6.6a9 9 0 1 0 12.8 0"/>',
    "play": '<path d="M7 4l13 8-13 8z"/>',
    "stop": '<rect x="6" y="6" width="12" height="12" rx="2"/>',
    "sync": '<path d="M20 12a8 8 0 0 1-14 5M4 12a8 8 0 0 1 14-5"/><path d="M18 3v4h-4M6 21v-4h4"/>',
    "folder": '<path d="M3 6a1 1 0 0 1 1-1h5l2 2h9a1 1 0 0 1 1 1v10a1 1 0 0 1-1 1H4a1 1 0 0 1-1-1z"/>',
    "glasses": '<circle cx="6.5" cy="14" r="3.5"/><circle cx="17.5" cy="14" r="3.5"/>'
               '<path d="M10 14h4M3 14L5 6M21 14l-2-8"/>',
}


def svg(name: str, color: str = "#E8EAF6", width: float = 1.8) -> str:
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="none" stroke="{color}" '
            f'stroke-width="{width}" stroke-linecap="round" stroke-linejoin="round">{_PATHS[name]}</svg>')


def pixmap(name: str, size: int = 24, color: str = "#E8EAF6") -> QPixmap:
    pm = QPixmap(size, size)
    pm.fill(Qt.transparent)
    renderer = QSvgRenderer(QByteArray(svg(name, color).encode()))
    painter = QPainter(pm)
    renderer.render(painter)
    painter.end()
    return pm


def icon(name: str, color: str = "#E8EAF6", size: int = 24) -> QIcon:
    return QIcon(pixmap(name, size, color))


NAMES = tuple(_PATHS)
