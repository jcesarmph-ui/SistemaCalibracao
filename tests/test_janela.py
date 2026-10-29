"""Janela principal em modo offscreen (sem abrir nada na tela)."""

import os
from datetime import date

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
from calibracao.interface.janela import JanelaPrincipal  # noqa: E402
from calibracao.regras.avaliacao import Resultado  # noqa: E402

HOJE = date(2026, 10, 29)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def janela(app, tmp_path):
    repo = Repositorio.abrir(tmp_path / "calibracao.db", HOJE)
    for codigo, data in [("TRE-901", date(2025, 10, 20)),   # pendente em outubro
                         ("TRE-902", date(2025, 11, 5)),    # novembro
                         ("TRE-903", date(2025, 9, 1)),     # vencida
                         ("TRE-904", None)]:                # sem calibração no programa
        plano = repo.incluir_plano(Plano(f"Plano {codigo}"))
        ponto = repo.incluir_ponto(PontoPlano(plano, "VERIFICACAO", "Aspecto geral"))
        instrumento = repo.incluir_instrumento(Instrumento(
            codigo, "Trena", localizacao="Expedição", periodicidade_meses=12, plano_id=plano))
        if data:
            repo.registrar_calibracao(NovaCalibracao(instrumento, data, [
                PontoMedido(ponto, escolha=Resultado.APROVADO)]), HOJE)
    tela = JanelaPrincipal(repo, tmp_path, HOJE)
    yield tela
    tela.close()
    repo.fechar()


def texto(rotulo):
    return rotulo.text()


def test_paineis_do_mes(janela):
    assert janela.titulos_paineis["mes"] == "CALIBRAÇÕES DE OUTUBRO"
    assert janela.titulos_paineis["proximo_mes"] == "CALIBRAÇÕES DE NOVEMBRO"
    assert "1 pendente" in texto(janela.valores_indicadores["mes"])
    assert texto(janela.valores_indicadores["proximo_mes"]) == "1"
    assert ">1<" in texto(janela.valores_indicadores["vencidas"])


@pytest.mark.parametrize(("painel", "codigo"),
                         [("mes", "TRE-901"), ("proximo_mes", "TRE-902"), ("vencidas", "TRE-903")])
def test_clicar_no_painel_mostra_os_instrumentos(janela, painel, codigo):
    janela.mostrar_lista_do_painel(painel, janela.aba_instrumentos)
    lista = janela._lista_aberta
    tabela = lista.findChild(type(janela.tabela_cronograma))
    assert tabela.rowCount() == 1
    assert tabela.item(0, 0).text() == codigo
    assert tabela.item(0, 2).text() == "Expedição"
    lista.close()


def test_cronograma_filtra_sem_calibracao(janela):
    janela.filtro_cronograma.setCurrentText("Sem calibração no programa")
    assert janela.tabela_cronograma.rowCount() == 1
    assert janela.tabela_cronograma.item(0, 0).text() == "TRE-904"


def test_cadastrar_instrumento_pela_tela(janela):
    aba = janela.aba_instrumentos
    aba.novo_instrumento()
    aba.campos["codigo"].setText("PAQ-950")
    aba.campos["tipo"].setText("Paquímetro")
    aba.campos["periodicidade_meses"].setText("12")
    aba.salvar_instrumento()
    assert "salvo" in aba.avisos.text()
    assert texto(janela.valores_indicadores["instrumentos"]) == "5"


def test_erro_de_digitacao_aparece_em_vermelho(janela):
    aba = janela.aba_instrumentos
    aba.novo_instrumento()
    aba.campos["codigo"].setText("TRE-901")  # já existe
    aba.campos["tipo"].setText("Trena")
    aba.campos["periodicidade_meses"].setText("doze")
    aba.salvar_instrumento()
    assert "número inteiro" in aba.avisos.text()
    aba.campos["periodicidade_meses"].setText("12")
    aba.salvar_instrumento()
    assert "Já existe" in aba.avisos.text()
    assert "#ef5350" in aba.avisos.styleSheet()
