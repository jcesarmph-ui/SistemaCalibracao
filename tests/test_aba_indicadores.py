"""Aba Indicadores: painel montado pelo usuário, montador que só oferece o que faz sentido,
desfazer das 3 últimas mudanças e modo consulta. Dados fictícios."""

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
from calibracao.interface.aba_indicadores import (  # noqa: E402
    AbaIndicadores,
    CartaoGrafico,
    JanelaGrafico,
)
from calibracao.regras import indicadores as ind  # noqa: E402
from calibracao.regras.condicao import ParecerFinal  # noqa: E402

HOJE = date(2026, 11, 20)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def repo(tmp_path):
    with Repositorio.abrir(tmp_path / "calibracao.db", HOJE) as repositorio:
        plano = repositorio.incluir_plano(Plano("Plano PAQ-900"))
        ponto = repositorio.incluir_ponto(PontoPlano(
            plano, "NUMERICO", "50", valor_nominal=50.0, unidade="mm",
            tolerancia_inferior=-0.05, tolerancia_superior=0.05, incerteza=0.01))
        for codigo, valor in (("PAQ-900", 50.03), ("PAQ-901", 50.01)):
            instrumento = repositorio.incluir_instrumento(Instrumento(
                codigo, "Paquímetro", localizacao="Usinagem", periodicidade_meses=12,
                plano_id=plano))
            repositorio.registrar_calibracao(NovaCalibracao(
                instrumento, date(2026, 11, 10), [PontoMedido(ponto, valor=valor,
                                                              incerteza=0.01)],
                parecer_final=ParecerFinal.APROVADO, laboratorio="Lab A", custo=180.0), HOJE)
        yield repositorio


@pytest.fixture
def aba(app, repo):
    tela = AbaIndicadores(repo, HOJE)
    tela.redesenhar()
    return tela


def cartoes(aba):
    return [aba.grade.itemAt(i).widget() for i in range(aba.grade.count())
            if isinstance(aba.grade.itemAt(i).widget(), CartaoGrafico)]


def test_painel_comeca_com_4_graficos_e_os_numeros(aba):
    assert [c.title() for c in cartoes(aba)] == [d.titulo for d in ind.PAINEL_INICIAL]
    assert aba.numeros["mes"][0].text() == "R$ 360,00"
    assert aba.numeros["prazo"][0].text() == "100%"


def test_montador_so_oferece_o_que_faz_sentido(aba):
    janela = JanelaGrafico(aba)
    janela.medida.setCurrentText(ind.QTD_INSTRUMENTOS)
    assert [janela.separar.itemText(i) for i in range(janela.separar.count())] == [
        ind.TIPO, ind.LOCALIZACAO]
    assert not janela.cor.isEnabled() and not janela.filtros[ind.PARECER].isEnabled()
    assert janela.ok.isEnabled()


def test_grafico_vazio_nao_pode_ser_adicionado(aba):
    janela = JanelaGrafico(aba)
    janela.filtros[ind.PARECER].setCurrentText("Reprovado - Desativado")
    assert not janela.ok.isEnabled()
    assert "Mude alguma opção" in janela.aviso.text()
    assert janela.titulo.text() == "CALIBRAÇÕES REPROVADAS POR MÊS"  # escreve sozinho


def test_exemplo_preenche_e_titulo_mexido_fica(aba):
    janela = JanelaGrafico(aba)
    janela.titulo.setText("MEU TÍTULO")
    janela.titulo.textEdited.emit("MEU TÍTULO")
    janela.periodo.setCurrentText(ind.ESTE_ANO)
    assert janela.titulo.text() == "MEU TÍTULO"


def test_adicionar_editar_tirar_e_desfazer(aba, repo, monkeypatch):
    assert not aba.desfazer.isEnabled()
    aba.adicionar_definicao(ind.DefinicaoGrafico(ind.CUSTO, ind.TIPO, titulo="CUSTO POR TIPO"))
    assert cartoes(aba)[-1].title() == "CUSTO POR TIPO" and aba.desfazer.isEnabled()
    novo = repo.listar_graficos()[-1][0]
    aba.salvar_edicao(novo, ind.DefinicaoGrafico(ind.CUSTO, ind.ANO, titulo="CUSTO POR ANO"))
    assert cartoes(aba)[-1].title() == "CUSTO POR ANO"
    monkeypatch.setattr(aba, "confirmar_tirar", lambda titulo: True)
    primeiro = repo.listar_graficos()[0][0]
    aba.tirar_grafico(primeiro)
    assert len(cartoes(aba)) == 4
    aba.desfazer_ultima()                       # volta o tirado, no mesmo lugar
    assert cartoes(aba)[0].title() == ind.PAINEL_INICIAL[0].titulo
    aba.desfazer_ultima()                       # desfaz a edição
    assert cartoes(aba)[-1].title() == "CUSTO POR TIPO"
    aba.desfazer_ultima()                       # desfaz a inclusão
    assert len(cartoes(aba)) == 4 and not aba.desfazer.isEnabled()


def test_desfazer_so_as_3_ultimas(aba):
    for n in range(5):
        aba.adicionar_definicao(ind.DefinicaoGrafico(ind.CUSTO, ind.TIPO, titulo=f"G{n}"))
    assert len(aba.desfazer_lista) == 3
    for _ in range(3):
        aba.desfazer_ultima()
    assert [c.title() for c in cartoes(aba)][-2:] == ["G0", "G1"]  # os 2 primeiros ficam


def test_tirar_cancelado_nao_tira(aba, monkeypatch):
    monkeypatch.setattr(aba, "confirmar_tirar", lambda titulo: False)
    aba.tirar_grafico(aba.repo.listar_graficos()[0][0])
    assert len(cartoes(aba)) == 4 and not aba.desfazer_lista


def test_modo_consulta_so_ve(aba):
    aba.definir_edicao(False)
    aba.redesenhar()
    assert aba.adicionar.isHidden() and aba.desfazer.isHidden()
    assert all(c.editar.isHidden() and c.tirar.isHidden() for c in cartoes(aba))
