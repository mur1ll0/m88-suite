# -*- mode: python ; coding: utf-8 -*-
# Build: desktop\packaging\build.bat  (gera desktop\dist\M88Suite\M88Suite.exe)
from PyInstaller.utils.hooks import collect_all

datas, binaries, hiddenimports = [], [], []
for package in ("bleak", "winrt", "av", "pyvirtualcam"):
    d, b, h = collect_all(package)
    datas += d
    binaries += b
    hiddenimports += h

a = Analysis(
    ["launch.py"],
    pathex=["../src"],
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports,
    excludes=["tkinter", "pytest", "PySide6.QtWebEngineCore", "PySide6.Qt3DCore", "PySide6.QtQuick"],
    noarchive=False,
)
# O app usa so Qt Widgets/SVG: remove OpenGL por software e modulos Qt que nao sao carregados.
UNUSED = ("opengl32sw", "Qt6Quick", "Qt6Qml", "Qt6Pdf", "Qt6VirtualKeyboard", "Qt6Network", "QtNetwork",
          "Qt6OpenGL", "QtOpenGL", "Qt6QmlModels", "Qt6QmlMeta", "Qt6QmlWorkerScript")
a.binaries = [b for b in a.binaries if not any(name.lower() in b[0].lower() for name in UNUSED)]

pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="M88Suite",
    icon="m88suite.ico",
    version="version_info.txt",
    console=False,
    upx=False,
)
coll = COLLECT(exe, a.binaries, a.datas, name="M88Suite", upx=False)
