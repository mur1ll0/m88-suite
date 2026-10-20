"""Tema visual (escuro, fontes grandes) da M88 Suite."""

ACCENT = "#4F8CFF"
OK = "#3DDC97"
WARN = "#FFB547"
BAD = "#FF5C6C"
BG = "#0F1220"
SURFACE = "#171B2E"
SURFACE_2 = "#1F2440"
TEXT = "#E8EAF6"
MUTED = "#9AA3C7"

BASE_FONT_PT = 12

QSS = f"""
* {{ font-family: "Segoe UI", "Inter", sans-serif; font-size: {BASE_FONT_PT}pt; color: {TEXT}; }}
QMainWindow, QWidget#root {{ background: {BG}; }}
QWidget#sidebar {{ background: {SURFACE}; border-right: 1px solid {SURFACE_2}; }}
QListWidget#nav {{ background: transparent; border: none; outline: none; padding: 8px; }}
QListWidget#nav::item {{ padding: 12px 14px; margin: 3px 0; border-radius: 10px; color: {MUTED}; }}
QListWidget#nav::item:selected {{ background: {SURFACE_2}; color: {TEXT}; }}
QListWidget#nav::item:hover {{ background: {SURFACE_2}; }}
QLabel#title {{ font-size: {BASE_FONT_PT + 10}pt; font-weight: 600; }}
QLabel#subtitle {{ color: {MUTED}; font-size: {BASE_FONT_PT}pt; }}
QLabel#brand {{ font-size: {BASE_FONT_PT + 4}pt; font-weight: 700; padding: 18px 18px 6px 18px; }}
QFrame#card {{ background: {SURFACE}; border: 1px solid {SURFACE_2}; border-radius: 16px; }}
QLabel#cardTitle {{ color: {MUTED}; font-size: {BASE_FONT_PT - 1}pt; }}
QLabel#cardValue {{ font-size: {BASE_FONT_PT + 8}pt; font-weight: 600; }}
QLabel#pill {{ border-radius: 12px; padding: 4px 12px; font-weight: 600; }}
QPushButton {{ background: {SURFACE_2}; border: 1px solid #2A3157; border-radius: 10px; padding: 10px 18px; }}
QPushButton:hover {{ border-color: {ACCENT}; }}
QPushButton:disabled {{ color: #5B6488; border-color: {SURFACE_2}; }}
QPushButton#primary {{ background: {ACCENT}; border: none; color: white; font-weight: 600; }}
QPushButton#primary:hover {{ background: #6A9EFF; }}
QPushButton#danger {{ background: transparent; border: 1px solid {BAD}; color: {BAD}; }}
QComboBox, QLineEdit, QSpinBox {{ background: {SURFACE_2}; border: 1px solid #2A3157; border-radius: 8px; padding: 8px 10px; }}
QComboBox QAbstractItemView {{ background: {SURFACE_2}; selection-background-color: {ACCENT}; }}
QCheckBox::indicator {{ width: 20px; height: 20px; }}
QListWidget#files, QPlainTextEdit {{ background: {SURFACE}; border: 1px solid {SURFACE_2}; border-radius: 12px; padding: 6px; }}
QLabel#video {{ background: #05060C; border-radius: 16px; color: {MUTED}; }}
QProgressBar {{ background: {SURFACE_2}; border: none; border-radius: 6px; height: 12px; text-align: center; }}
QProgressBar::chunk {{ background: {OK}; border-radius: 6px; }}
"""


def rgba(color: str, alpha: float) -> str:
    """Converte '#RRGGBB' em rgba() (o Qt le '#RRGGBBAA' como '#AARRGGBB')."""
    r, g, b = (int(color[i:i + 2], 16) for i in (1, 3, 5))
    return f"rgba({r}, {g}, {b}, {alpha})"


def pill_style(color: str) -> str:
    return f"background: {rgba(color, 0.18)}; color: {color};"
