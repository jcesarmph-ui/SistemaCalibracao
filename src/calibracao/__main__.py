"""Ponto de entrada: `python -m calibracao` e o `.exe` gerado pelo PyInstaller."""

import sys

from calibracao.interface.app import main

if __name__ == "__main__":
    sys.exit(main())
