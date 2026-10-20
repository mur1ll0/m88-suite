"""Compacta dist/M88Suite em dist/M88Suite-<versao>-windows.zip (pacote de release)."""
import shutil
from pathlib import Path

import m88suite

dist = Path(__file__).resolve().parents[1] / "dist"
archive = shutil.make_archive(str(dist / f"M88Suite-{m88suite.__version__}-windows"), "zip", dist, "M88Suite")
print(f"{archive} ({Path(archive).stat().st_size / 1e6:.0f} MB)")
