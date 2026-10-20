"""Script de entrada do PyInstaller (o pacote usa imports relativos)."""
import sys

from m88suite.app import main

sys.exit(main())
