"""Abre o programa: banco da pasta de dados (com o backup do dia) e a janela em tela cheia."""

import ctypes
import getpass
import os
import platform
import sys
from pathlib import Path

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QApplication, QMessageBox

from calibracao.dados.local_banco import eh_copia, local_do_banco
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


class BancoNaoEncontrado(Exception):
    pass


def abrir_banco(pasta: Path) -> tuple[Repositorio, str | None]:
    """Abre o banco da pasta e diz se é uma CÓPIA (devolve o caminho do oficial) ou não (None).

    Nunca cria banco vazio: sem o arquivo, o problema aparece em vez de ficar escondido. Banco
    sem lugar oficial marcado (o da entrega) adota este lugar como oficial.
    """
    banco = pasta / "calibracao.db"
    if not banco.is_file():
        raise BancoNaoEncontrado(
            f"Não achei o arquivo do banco de dados:\n{banco}\n\nO programa precisa da pasta "
            "\"dados\" (com o calibracao.db) ao lado dele. Confira se a pasta foi copiada ou "
            "movida inteira.")
    repositorio = Repositorio.abrir(banco)
    oficial = repositorio.pasta_oficial()
    if oficial is None:
        repositorio.marcar_pasta_oficial(local_do_banco(banco))
        return repositorio, None
    return repositorio, oficial if eh_copia(banco, oficial) else None


def main() -> int:
    if sys.platform == "win32":
        # Sem isso o Windows agrupa a janela sob o python.exe e mostra o ícone do Python.
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("MG.CalibracaoInstrumentos")
    app = QApplication(sys.argv)
    pasta = pasta_dados_padrao()
    try:
        repositorio, oficial = abrir_banco(pasta)
    except Exception as erro:  # noqa: BLE001 — qualquer falha ao abrir vira mensagem na tela
        QMessageBox.critical(None, "Erro ao abrir o banco de dados", str(erro))
        return 1
    icone = pasta / "icone_mg.png"
    if icone.is_file():
        app.setWindowIcon(QIcon(str(icone)))
    # Quem está usando (para a trava de edição): usuário do Windows e nome do computador.
    janela = JanelaPrincipal(repositorio, pasta, identidade=(getpass.getuser(), platform.node()),
                             copia_de=oficial)
    janela.showMaximized()
    try:
        return app.exec()
    finally:
        repositorio.fechar()


if __name__ == "__main__":
    sys.exit(main())
