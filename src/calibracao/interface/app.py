"""Abre o programa: banco da pasta de dados (com o backup do dia) e a janela em tela cheia."""

import ctypes
import getpass
import os
import platform
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from calibracao.dados.repositorio import Repositorio
from calibracao.interface.janela import JanelaPrincipal


def pasta_dados_padrao() -> Path:
    """Variável CALIBRACAO_DADOS, senão dados/ ao lado do .exe (ou na pasta do projeto)."""
    if os.environ.get("CALIBRACAO_DADOS"):
        return Path(os.environ["CALIBRACAO_DADOS"])
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / "dados"
    if (Path.cwd() / "dados").is_dir():
        return Path.cwd() / "dados"
    return Path(__file__).resolve().parents[3] / "dados"


def main() -> int:
    if sys.platform == "win32":
        # Sem isso o Windows agrupa a janela sob o python.exe e mostra o ícone do Python.
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MG.CalibracaoInstrumentos")
    app = QApplication(sys.argv)
    pasta = pasta_dados_padrao()
    try:
        repositorio = Repositorio.abrir(pasta / "calibracao.db")
    except Exception as erro:  # noqa: BLE001 — qualquer falha ao abrir vira mensagem na tela
        QMessageBox.critical(None, "Erro ao abrir o banco de dados", str(erro))
        return 1
    icone = pasta / "icone_mg.png"
    if icone.is_file():
        app.setWindowIcon(QIcon(str(icone)))
    # Quem está usando (para a trava de edição): usuário do Windows e nome do computador.
    janela = JanelaPrincipal(repositorio, pasta, identidade=(getpass.getuser(), platform.node()))
    janela.showMaximized()
    try:
        return app.exec()
    finally:
        repositorio.fechar()


if __name__ == "__main__":
    sys.exit(main())
