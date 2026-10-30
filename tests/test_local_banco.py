"""Lugar oficial do banco: cópia só consulta e nunca criar banco vazio."""

import os
import shutil
from datetime import date

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from calibracao.dados.local_banco import eh_copia, local_do_banco  # noqa: E402
from calibracao.dados.repositorio import Repositorio  # noqa: E402
from calibracao.interface.app import BancoNaoEncontrado, abrir_banco  # noqa: E402
from calibracao.interface.janela import JanelaPrincipal  # noqa: E402

HOJE = date(2026, 10, 30)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def oficial(tmp_path):
    """Pasta "da rede" com o programa: Programa/dados/calibracao.db."""
    dados = tmp_path / "Programa" / "dados"
    dados.mkdir(parents=True)
    Repositorio.abrir(dados / "calibracao.db", HOJE).fechar()
    return dados


def test_mesmo_arquivo_nao_e_copia(oficial):
    banco = oficial / "calibracao.db"
    assert not eh_copia(banco, local_do_banco(banco))
    # o mesmo arquivo escrito com outras maiúsculas (ex.: outro PC) também não é cópia
    assert not eh_copia(banco, local_do_banco(banco).upper())


def test_arquivo_copiado_e_copia(oficial, tmp_path):
    copia = tmp_path / "Area de trabalho" / "dados"
    shutil.copytree(oficial, copia)
    assert eh_copia(copia / "calibracao.db", local_do_banco(oficial / "calibracao.db"))


def test_oficial_fora_do_alcance_compara_o_caminho(oficial, tmp_path):
    assert eh_copia(oficial / "calibracao.db", str(tmp_path / "servidor" / "calibracao.db"))


def test_sem_banco_nao_cria_banco_vazio(tmp_path):
    (tmp_path / "dados").mkdir()
    with pytest.raises(BancoNaoEncontrado, match="calibracao.db"):
        abrir_banco(tmp_path / "dados")
    assert not (tmp_path / "dados" / "calibracao.db").exists()


def test_primeira_abertura_adota_o_lugar_oficial(oficial):
    repo, copia_de = abrir_banco(oficial)
    assert copia_de is None
    assert repo.pasta_oficial() == local_do_banco(oficial / "calibracao.db")
    repo.fechar()
    repo, copia_de = abrir_banco(oficial)  # abrir de novo do mesmo lugar: normal
    assert copia_de is None
    repo.fechar()


def test_pasta_copiada_abre_como_copia(oficial, tmp_path):
    abrir_banco(oficial)[0].fechar()
    copia = tmp_path / "Copia" / "dados"
    shutil.copytree(oficial, copia)
    repo, copia_de = abrir_banco(copia)
    assert copia_de == local_do_banco(oficial / "calibracao.db")
    repo.fechar()


def test_janela_da_copia_so_consulta_e_mudar_torna_oficial(app, oficial, tmp_path):
    abrir_banco(oficial)[0].fechar()
    copia = tmp_path / "Nova pasta" / "dados"
    shutil.copytree(oficial, copia)
    repo, copia_de = abrir_banco(copia)
    janela = JanelaPrincipal(repo, copia, HOJE, identidade=("ana", "PC-1"), copia_de=copia_de)
    try:
        assert repo.modo_consulta
        assert not janela.aviso_copia.isHidden()
        assert "CÓPIA" in janela.aviso_copia.text()
        assert "Programa" in janela.aviso_copia.text()  # mostra onde fica o oficial
        assert janela.rotulo_modo.text() == "Modo consulta - cópia do banco"
        janela.pedir_edicao()  # clicar no canto não passa para edição na cópia
        assert repo.modo_consulta
        assert not janela.confirmar_pasta_oficial("sim")
        assert repo.modo_consulta
        assert janela.confirmar_pasta_oficial("mudar")
        assert not repo.modo_consulta
        assert janela.aviso_copia.isHidden()
        assert janela.rotulo_modo.text() == "Modo edição"
        assert repo.pasta_oficial() == local_do_banco(copia / "calibracao.db")
    finally:
        janela.close()
        repo.fechar()
