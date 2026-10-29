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
from calibracao.regras.condicao import Condicao, ParecerFinal  # noqa: E402

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
                PontoMedido(ponto, escolha=Resultado.APROVADO)],
                parecer_final=ParecerFinal.APROVADO), HOJE)
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
    aba.campos["custo_compra"].setText("R$ 350,50")
    aba.campos["responsavel"].setText("Fulano")
    aba.salvar_instrumento()
    assert "salvo" in aba.avisos.text()
    assert texto(janela.valores_indicadores["instrumentos"]) == "5"
    salvo = next(i for i in janela.repo.listar_instrumentos() if i.codigo == "PAQ-950")
    assert (salvo.custo_compra, salvo.responsavel) == (350.5, "Fulano")
    assert aba.campos["custo_compra"].text() == "350,5"


def codigos_da_lista(aba):
    return [aba.tabela.item(linha, 0).text() for linha in range(aba.tabela.rowCount())]


def test_filtros_de_tipo_e_localizacao(janela):
    aba = janela.aba_instrumentos
    janela.repo.incluir_instrumento(Instrumento("PAQ-950", "Paquímetro", localizacao="CT-01"))
    janela.atualizar()
    aba.filtro_tipo.setCurrentText("Paquímetro")
    assert codigos_da_lista(aba) == ["PAQ-950"]
    aba.filtro_tipo.setCurrentText("Todos os tipos")
    aba.filtro_local.setCurrentText("Expedição")
    assert codigos_da_lista(aba) == ["TRE-901", "TRE-902", "TRE-903", "TRE-904"]


def test_mudar_condicao_pela_tela(janela):
    aba = janela.aba_instrumentos
    escolher(aba, "TRE-901")
    aba.aplicar_condicao(Condicao.DESATIVADO, date(2026, 10, 20), "Fita rompida")
    assert "Desativado" in aba.avisos.text()
    assert "Desativado" in aba.condicao_atual.text()
    assert aba.tabela_historico.item(0, 2).text() == "Fita rompida"
    # sai do cronograma e dos indicadores, mas continua na lista (filtro Desativados)
    assert texto(janela.valores_indicadores["instrumentos"]) == "3"
    assert "1 pendente" not in texto(janela.valores_indicadores["mes"])
    assert "TRE-901" not in codigos_da_lista(aba)  # a lista abre sem os desativados
    aba.filtro_condicao.setCurrentText("Desativados")
    assert codigos_da_lista(aba) == ["TRE-901"]
    assert aba.tabela.item(0, 3).text() == "20/10/2026"


def test_mudar_condicao_recusa_data_futura(janela):
    aba = janela.aba_instrumentos
    escolher(aba, "TRE-902")
    aba.aplicar_condicao(Condicao.ORIENTACAO_INDICATIVA, date(2026, 11, 1), "")
    assert "futuro" in aba.avisos.text()
    assert "#ef5350" in aba.avisos.styleSheet()


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


def escolher(aba, codigo):
    for linha in range(aba.tabela.rowCount()):
        if aba.tabela.item(linha, 0).text() == codigo:
            aba.tabela.selectRow(linha)
            return
    raise AssertionError(codigo)


@pytest.fixture
def plano_da_trena(janela):
    """TRE-901 com um ponto numérico sem U (como as trenas que vieram da planilha)."""
    aba = janela.aba_instrumentos
    repo = janela.repo
    plano_id = repo.obter_instrumento(
        next(i.id for i in repo.listar_instrumentos() if i.codigo == "TRE-901")).plano_id
    repo.incluir_ponto(PontoPlano(plano_id, "NUMERICO", "300", valor_nominal=300.0,
                                  tolerancia_inferior=-0.5, tolerancia_superior=0.5))
    escolher(aba, "TRE-901")
    return aba.painel_plano, plano_id


def test_plano_avisa_e_aceita_a_incerteza(janela, plano_da_trena):
    painel, plano_id = plano_da_trena
    assert "1 ponto(s) sem Incerteza (U)" in painel.avisos.text()
    linha = painel.tabela.rowCount() - 1
    painel.tabela.item(linha, 12).setText("0,2")  # coluna Incerteza (U), com vírgula
    painel.salvar_plano()
    assert "Plano salvo" in painel.avisos.text()
    assert janela.repo.listar_pontos(plano_id)[-1].incerteza == 0.2


def test_plano_recusa_texto_que_nao_e_numero(janela, plano_da_trena):
    painel, plano_id = plano_da_trena
    painel.tabela.item(painel.tabela.rowCount() - 1, 12).setText("zero vírgula dois")
    painel.salvar_plano()
    assert "não é um número" in painel.avisos.text()
    assert janela.repo.listar_pontos(plano_id)[-1].incerteza is None


def test_plano_adiciona_ponto(janela, plano_da_trena):
    painel, plano_id = plano_da_trena
    antes = len(janela.repo.listar_pontos(plano_id))
    painel.adicionar_ponto()
    linha = painel.tabela.rowCount() - 1
    painel.tabela.item(linha, 3).setText("900")
    painel.tabela.item(linha, 4).setText("900")
    painel.salvar_plano()
    assert len(janela.repo.listar_pontos(plano_id)) == antes + 1


def test_salvar_plano_mantem_o_numero_original_da_planilha(janela):
    aba = janela.aba_instrumentos
    repo = janela.repo
    plano_id = repo.obter_instrumento(
        next(i.id for i in repo.listar_instrumentos() if i.codigo == "TRE-902")).plano_id
    repo.incluir_ponto(PontoPlano(plano_id, "NUMERICO", "300", ordem_original="7",
                                  valor_nominal=300.0, tolerancia_inferior=-0.5,
                                  tolerancia_superior=0.5))
    escolher(aba, "TRE-902")
    painel = aba.painel_plano
    assert not painel.tem_alteracao()
    painel.tabela.item(painel.tabela.rowCount() - 1, 12).setText("0,2")
    assert painel.tem_alteracao()
    painel.salvar_plano()
    assert repo.listar_pontos(plano_id)[-1].ordem_original == "7"
