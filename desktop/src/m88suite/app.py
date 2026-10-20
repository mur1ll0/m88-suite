"""Ponto de entrada da M88 Suite (Windows)."""
from __future__ import annotations

import logging
import sys
from pathlib import Path

from PySide6.QtWidgets import QApplication

from .ui import theme
from .ui.main_window import MainWindow

LOG_DIR = Path.home() / "M88Suite" / "logs"


def selftest() -> int:
    """Verifica, sem o oculos, se o app (ou o EXE) carrega UI, decodificador, BLE e webcam virtual."""
    import importlib
    import os
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")
    report = LOG_DIR / "selftest.txt"
    lines = []
    for mod in ("av", "pyvirtualcam", "bleak", "bleak.backends.winrt.client", "numpy"):
        try:
            importlib.import_module(mod)
            lines.append(f"ok   {mod}")
        except Exception as e:  # noqa: BLE001 - o relatorio precisa de qualquer falha
            lines.append(f"FALHA {mod}: {e}")
    from .core.manager import DeviceManager, Listener
    app = QApplication.instance() or QApplication(sys.argv)
    app.setStyleSheet(theme.QSS)
    window = MainWindow(DeviceManager(Listener()))
    window.show()
    app.processEvents()
    lines.append(f"ok   janela {window.width()}x{window.height()}")
    window.close()
    ok = not any(line.startswith("FALHA") for line in lines)
    lines.append("RESULTADO: " + ("OK" if ok else "FALHA"))
    text = "\n".join(lines) + "\n"
    report.write_text(text, encoding="utf-8")
    print(text, end="")
    return 0 if ok else 1


def main() -> int:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    if "--selftest" in sys.argv:
        return selftest()
    logging.basicConfig(level=logging.INFO, filename=LOG_DIR / "m88suite.log",
                        format="%(asctime)s %(levelname)s %(name)s: %(message)s")
    app = QApplication(sys.argv)
    app.setApplicationName("M88 Suite")
    app.setStyleSheet(theme.QSS)
    window = MainWindow()
    window.show()
    return app.exec()


if __name__ == "__main__":
    sys.exit(main())
