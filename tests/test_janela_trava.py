"""Modo consulta na tela: duas janelas (dois computadores) no mesmo banco."""

import os
from datetime import date

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from calibracao.dados.repositorio import Instrumento, Plano, PontoPlano, Repositorio  # noqa: E402
from calibracao.interface.janela import JanelaPrincipal  # noqa: E402

HOJE = date(2026, 10, 29)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def duas_janelas(app, tmp_path):
    banco = tmp_path / "calibracao.db"
    with Repositorio.abrir(banco, HOJE) as repo:
        plano = repo.incluir_plano(Plano("Plano TRE-901"))
        repo.incluir_ponto(PontoPlano(plano, "VERIFICACAO", "Aspecto geral"))
        repo.incluir_instrumento(Instrumento("TRE-901", "Trena", plano_id=plano,
                                             periodicidade_meses=12))
    repo_a, repo_b = Repositorio.abrir(banco, HOJE), Repositorio.abrir(banco, HOJE)
    a = JanelaPrincipal(repo_a, tmp_path, HOJE, identidade=("ana", "PC-1"))
    b = JanelaPrincipal(repo_b, tmp_path, HOJE, identidade=("beto", "PC-2"))
    yield a, b
    for janela in (a, b):
        janela.close()
        janela.repo.fechar()


def visivel(widget):
    return not widget.isHidden()  # as janelas do teste não aparecem na tela


def test_quem_abre_depois_so_consulta(duas_janelas):
    a, b = duas_janelas
    assert not visivel(a.faixa_consulta)
    assert visivel(b.faixa_consulta)
    assert "ana (PC-1) está editando desde" in b.texto_consulta.text()
    assert "SOMENTE CONSULTA" in b.windowTitle()
    aba = b.aba_instrumentos
    for botao in (aba.novo, aba.salvar, aba.mudar_condicao, aba.lixeira,
                  aba.painel_plano.salvar, aba.painel_calibracoes.registrar,
                  b.aba_lixeira.restaurar):
        assert not visivel(botao)
    assert aba.campos["codigo"].isReadOnly()
    aba.tabela.selectRow(0)
    assert aba.titulo_dados.text() == "Consultando TRE-901"
    assert visivel(aba.painel_calibracoes.grafico)  # consultar continua liberado
    assert visivel(a.aba_instrumentos.salvar)


def test_consulta_ve_o_que_o_outro_salvou(duas_janelas):
    a, b = duas_janelas
    a.repo.incluir_instrumento(Instrumento("TRE-902", "Trena"))
    b.a_cada_sinal()  # 30 segundos depois
    assert b.valores_indicadores["instrumentos"].text() == "2"


def test_quando_o_outro_fecha_da_para_passar_para_edicao(duas_janelas):
    a, b = duas_janelas
    a.close()
    b.a_cada_sinal()
    assert "ninguém está editando" in b.texto_consulta.text()
    b.pedir_edicao()
    assert not visivel(b.faixa_consulta)
    assert visivel(b.aba_instrumentos.salvar)
    assert not b.aba_instrumentos.campos["codigo"].isReadOnly()


def test_quem_perde_a_trava_vira_consulta(duas_janelas):
    a, b = duas_janelas
    a.repo.liberar_trava()           # como se a trava de A tivesse vencido…
    b.pedir_edicao()                 # …e B tivesse assumido
    a.a_cada_sinal()                 # A volta a dar sinal: percebe que perdeu
    assert visivel(a.faixa_consulta)
    assert "passou a editar" in a.texto_consulta.text()
    assert not visivel(a.aba_instrumentos.salvar)
