@echo off
rem Abre a M88 Suite usando o ambiente virtual do projeto.
cd /d "%~dp0"
if not exist ".venv\Scripts\pythonw.exe" (
  echo Criando ambiente e instalando dependencias, aguarde...
  python -m venv .venv || exit /b 1
  ".venv\Scripts\python.exe" -m pip install -q -e . || exit /b 1
)
start "" ".venv\Scripts\pythonw.exe" -m m88suite.app
