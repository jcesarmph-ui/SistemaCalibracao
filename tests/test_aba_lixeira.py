"""Aba Lixeira pela tela: listar, filtrar, restaurar e excluir de vez."""

import os
from datetime import date, datetime

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from calibracao.dados.repositorio import (  # noqa: E402
    Instrumento,
    NovaCalibracao,
    Plano,
    PontoMedido,
    PontoPlano,
    Repositorio,
)
from calibracao.interface.aba_lixeira import JanelaExcluir, quando  # noqa: E402
from calibracao.interface.janela import JanelaPrincipal  # noqa: E402
from calibracao.regras.avaliacao import Resultado  # noqa: E402
from calibracao.regras.condicao import ParecerFinal  # noqa: E402
from calibracao.regras.lixeira import Tipo  # noqa: E402

HOJE = date(2026, 10, 29)
AGORA = datetime(2026, 10, 29, 14, 5)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def janela(app, tmp_path):
    repo = Repositorio.abrir(tmp_path / "calibracao.db", HOJE)
    for codigo in ("TRE-901", "TRE-902"):
        plano = repo.incluir_plano(Plano(f"Plano {codigo}"))
        ponto = repo.incluir_ponto(PontoPlano(plano, "VERIFICACAO", "Aspecto geral"))
        instrumento = repo.incluir_instrumento(
            Instrumento(codigo, "Trena", periodicidade_meses=12, plano_id=plano))
    repo.registrar_calibracao(NovaCalibracao(  # só o TRE-902 tem calibração
        instrumento, date(2026, 10, 1), [PontoMedido(ponto, escolha=Resultado.APROVADO)],
        parecer_final=ParecerFinal.APROVADO), HOJE)
    tela = JanelaPrincipal(repo, tmp_path, HOJE)
    yield tela
    tela.close()
    repo.fechar()


def ids(repo):
    return {i.codigo: i.id for i in repo.listar_instrumentos()}


def escolher(aba, linha=0):
    aba.tabela.selectRow(linha)


def test_quando():
    assert quando("2026-10-29T14:05:00") == "29/10/2026 14:05"


def test_lista_e_filtra(janela):
    repo, aba = janela.repo, janela.aba_lixeira
    codigos = ids(repo)
    repo.enviar_para_lixeira(Tipo.INSTRUMENTO, codigos["TRE-901"], "Duplicado", AGORA)
    calibracao = repo.listar_calibracoes(codigos["TRE-902"])[0].id
    repo.enviar_para_lixeira(Tipo.CALIBRACAO, calibracao, None, AGORA)
    janela.atualizar()
    assert aba.tabela.rowCount() == 2
    aba.filtro.setCurrentText("Instrumentos")
    assert aba.tabela.rowCount() == 1
    assert aba.tabela.item(0, 1).text() == "TRE-901 — Trena"
    assert aba.tabela.item(0, 2).text() == "29/10/2026 14:05"
    assert aba.tabela.item(0, 3).text() == "Duplicado"
    aba.filtro.setCurrentText("Calibrações")
    assert aba.tabela.item(0, 1).text() == "TRE-902 — calibração de 01/10/2026"


def test_restaurar_volta_para_a_lista(janela):
    repo, aba = janela.repo, janela.aba_lixeira
    repo.enviar_para_lixeira(Tipo.INSTRUMENTO, ids(repo)["TRE-901"], None, AGORA)
    janela.atualizar()
    assert janela.valores_indicadores["instrumentos"].text() == "1"
    escolher(aba)
    aba.restaurar_item()
    assert "Restaurado" in aba.avisos.text()
    assert aba.tabela.rowCount() == 0
    assert janela.valores_indicadores["instrumentos"].text() == "2"


def test_restaurar_exige_o_pai(janela):
    repo, aba = janela.repo, janela.aba_lixeira
    instrumento = ids(repo)["TRE-902"]
    calibracao = repo.listar_calibracoes(instrumento)[0].id
    repo.enviar_para_lixeira(Tipo.CALIBRACAO, calibracao, None, AGORA)
    repo.enviar_para_lixeira(Tipo.INSTRUMENTO, instrumento, None, AGORA)
    janela.atualizar()
    aba.filtro.setCurrentText("Calibrações")
    escolher(aba)
    aba.restaurar_item()
    assert "Restaure primeiro o instrumento" in aba.avisos.text()
    assert "#ef5350" in aba.avisos.styleSheet()


def test_excluir_de_vez_so_com_excluir_digitado(app, janela):
    repo, aba = janela.repo, janela.aba_lixeira
    repo.enviar_para_lixeira(Tipo.INSTRUMENTO, ids(repo)["TRE-901"], None, AGORA)
    janela.atualizar()
    escolher(aba)
    item = aba.selecionado()
    confirmacao = JanelaExcluir(item)
    assert not confirmacao.confirmar.isEnabled()
    confirmacao.confirmacao.setText("EXCLUIR")
    assert confirmacao.confirmar.isEnabled()
    aba.excluir_de_vez(item, "EXCLUIR")
    assert "Excluído para sempre" in aba.avisos.text()
    assert repo.listar_lixeira() == []


def test_instrumento_com_calibracao_nao_sai_de_vez(janela):
    repo, aba = janela.repo, janela.aba_lixeira
    repo.enviar_para_lixeira(Tipo.INSTRUMENTO, ids(repo)["TRE-902"], None, AGORA)
    janela.atualizar()
    escolher(aba)
    aba.excluir_de_vez(aba.selecionado(), "EXCLUIR")
    assert "registros ligados" in aba.avisos.text()
    assert len(repo.listar_lixeira()) == 1
