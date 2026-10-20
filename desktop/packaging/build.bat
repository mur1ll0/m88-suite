@echo off
rem Gera desktop\dist\M88Suite\M88Suite.exe e desktop\dist\M88Suite-<versao>-windows.zip
setlocal
cd /d "%~dp0"
set "PY=%~dp0..\.venv\Scripts\python.exe"
if not exist "%PY%" goto :novenv
"%PY%" -m PyInstaller --noconfirm --clean --distpath "%~dp0..\dist" --workpath "%~dp0..\build" m88suite.spec
if errorlevel 1 exit /b 1
"%PY%" "%~dp0make_zip.py"
if errorlevel 1 exit /b 1
echo Pronto: %~dp0..\dist\M88Suite\M88Suite.exe
exit /b 0

:novenv
echo Ambiente nao encontrado. Na pasta desktop, rode:
echo   python -m venv .venv
echo   .venv\Scripts\python -m pip install -e .[dev] pyinstaller==6.11.1
exit /b 1
