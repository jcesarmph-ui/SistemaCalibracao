"""Indicadores (pedido de 2026-11-10): gráficos montados pelo usuário, números do painel, "mais
perto do limite" e o painel guardado no banco. Dados fictícios."""

import datetime
from datetime import date

import pytest

from calibracao.dados.repositorio import (
    Instrumento,
    NovaCalibracao,
    Plano,
    PontoMedido,
    PontoPlano,
    PontoRegistrado,
    Repositorio,
)
from calibracao.regras import indicadores as ind
from calibracao.regras.avaliacao import Resultado
from calibracao.regras.condicao import ParecerFinal

HOJE = date(2027, 11, 3)


def cal(data, instrumento="PAQ-001", tipo="Paquímetro", locais=("Usinagem",),
        laboratorio="Lab A", parecer="Aprovado", prazo=ind.NO_PRAZO_TXT, custo=100.0,
        limite=50.0):
    return ind.CalibracaoParaIndicador(data, instrumento, tipo, list(locais), laboratorio,
                                       parecer, prazo, custo, limite)


CALIBRACOES = [
    cal(date(2027, 10, 5), "PAQ-001", custo=180, limite=96),
    cal(date(2027, 10, 9), "MIC-001", "Micrômetro", ("Laboratório",), "Lab B",
        "Reprovado - Desativado", custo=220, limite=120),
    cal(date(2027, 9, 2), "TRE-001", "Trena", ("Caldeiraria", "Usinagem"), "MG (interna)",
        prazo=ind.COM_ATRASO_TXT, custo=0, limite=None),
    cal(date(2026, 12, 1), "PAQ-001", custo=150, limite=40),   # mais antiga do PAQ-001
    cal(date(2025, 5, 1), "PAQ-002", custo=999),               # fora dos 12 meses
]
INSTRUMENTOS = [ind.InstrumentoParaIndicador("PAQ-001", "Paquímetro", ["Usinagem"]),
                ind.InstrumentoParaIndicador("TRE-001", "Trena", ["Caldeiraria", "Usinagem"])]


def test_12_meses_terminam_no_mes_de_referencia():
    meses = ind.meses_do_periodo(ind.ULTIMOS_12, HOJE)
    assert len(meses) == 12 and meses[0] == (2026, 12) and meses[-1] == (2027, 11)
    assert ind.meses_do_periodo(ind.ANO_PASSADO, HOJE)[0] == (2026, 1)


def test_calibracoes_por_mes_com_cores_de_prazo():
    definicao = ind.DefinicaoGrafico(ind.QTD_CALIBRACOES, ind.MES, ind.PRAZO)
    resultado = ind.calcular(definicao, CALIBRACOES, INSTRUMENTOS, HOJE)
    assert len(resultado.categorias) == 12 and resultado.categorias[-2] == "out/27"
    assert list(resultado.series) == [ind.NO_PRAZO_TXT, ind.COM_ATRASO_TXT]  # verde, amarelo
    assert resultado.series[ind.NO_PRAZO_TXT][-2] == 2
    assert resultado.series[ind.COM_ATRASO_TXT][-3] == 1


def test_reprovadas_e_filtro_que_esvazia():
    reprovadas = ind.DefinicaoGrafico(ind.QTD_CALIBRACOES, ind.MES,
                                      filtros={ind.PARECER: "Reprovado - Desativado"})
    assert sum(ind.calcular(reprovadas, CALIBRACOES, [], HOJE).series[""]) == 1
    assert ind.titulo_automatico(reprovadas) == "CALIBRAÇÕES REPROVADAS POR MÊS"
    vazio = ind.DefinicaoGrafico(ind.QTD_CALIBRACOES, ind.MES,
                                 filtros={ind.TIPO: "Balança"})
    resultado = ind.calcular(vazio, CALIBRACOES, [], HOJE)
    assert resultado.vazio and "vazio" in resultado.aviso


def test_custo_por_laboratorio_do_maior_para_o_menor():
    definicao = ind.DefinicaoGrafico(ind.CUSTO, ind.LABORATORIO, forma=ind.DEITADAS)
    resultado = ind.calcular(definicao, CALIBRACOES, [], HOJE)
    assert resultado.categorias == ["Lab A", "Lab B", "MG (interna)"]
    assert resultado.series[""] == [330, 220, 0]
    assert resultado.unidade == "R$"


def test_instrumento_em_dois_locais_conta_nos_dois():
    definicao = ind.DefinicaoGrafico(ind.QTD_INSTRUMENTOS, ind.LOCALIZACAO)
    resultado = ind.calcular(definicao, [], INSTRUMENTOS, HOJE)
    assert dict(zip(resultado.categorias, resultado.series[""], strict=True)) == {
        "Usinagem": 2, "Caldeiraria": 1}


def test_so_oferece_o_que_faz_sentido():
    assert ind.separacoes_validas(ind.QTD_INSTRUMENTOS) == [ind.TIPO, ind.LOCALIZACAO]
    assert not ind.pode_dividir_em_cores(ind.CUSTO_MEDIO)
    ajustada = ind.ajustar(ind.DefinicaoGrafico(ind.QTD_INSTRUMENTOS, ind.MES, ind.PARECER,
                                                {ind.PARECER: "Aprovado"}))
    assert (ajustada.separar, ajustada.cor, ajustada.filtros) == (ind.TIPO, ind.SEM_CORES, {})


def test_mais_de_12_itens_mostra_os_maiores_e_avisa():
    muitas = [cal(date(2027, 10, 1), f"PAQ-{n:03d}", custo=n) for n in range(1, 21)]
    definicao = ind.DefinicaoGrafico(ind.CUSTO, ind.INSTRUMENTO)
    resultado = ind.calcular(definicao, muitas, [], HOJE)
    assert len(resultado.categorias) == 12 and resultado.categorias[0] == "PAQ-020"
    assert "12 maiores de 20" in resultado.nota


def test_mais_perto_do_limite_no_painel_e_no_relatorio():
    definicao = ind.DefinicaoGrafico(ind.PERTO_DO_LIMITE)
    painel = ind.calcular(definicao, CALIBRACOES, [], HOJE)  # última de cada instrumento
    assert painel.categorias == ["MIC-001", "PAQ-001", "PAQ-002"]
    assert painel.series[""] == [120, 96, 50]
    relatorio = ind.calcular(definicao, CALIBRACOES, [], date(2027, 9, 30), so_do_mes=True)
    assert relatorio.vazio  # em setembro só a trena, sem ponto numérico


def ponto(valor, incerteza=0.01, nominal=50.0, inferior=-0.05, superior=0.05, **kw):
    return PontoRegistrado(1, None, "NUMERICO", "50 mm", nominal, "mm", inferior, superior,
                           None, None, None, None, valor, incerteza, None, None,
                           kw.get("resultado", Resultado.APROVADO), None,
                           kw.get("nao_aplica", False))


def test_limite_usado_com_a_incerteza():
    assert ind.limite_usado([ponto(50.03)]) == 80.0     # (0,03 + 0,01) / 0,05
    assert ind.limite_usado([ponto(49.97)]) == 80.0     # lado de baixo
    assert ind.limite_usado([ponto(50.05)]) == 120.0    # fora
    assert ind.limite_usado([ponto(50.0)]) == 20.0      # desvio zero: ± U
    assert ind.limite_usado([ponto(50.02), ponto(50.04)]) == 100.0  # vale o pior
    assert ind.limite_usado([ponto(50.04, resultado=Resultado.NAO_APLICAVEL)]) is None
    assert ind.limite_usado([ponto(50.04, incerteza=None)]) is None  # sem U: não avaliado


def test_numeros_do_painel_e_media_no_primeiro_ano():
    numeros = ind.numeros(CALIBRACOES, HOJE, implantacao=date(2026, 11, 1))
    assert numeros.custo_12_meses == 550 and numeros.custo_do_mes == 0
    assert numeros.custo_medio_mes == pytest.approx(550 / 12)
    no_inicio = ind.numeros(CALIBRACOES, date(2027, 1, 31), implantacao=date(2026, 11, 1))
    assert no_inicio.custo_medio_mes == pytest.approx(150 / 3)  # nov, dez, jan


def test_definicao_vai_e_volta_do_json():
    definicao = ind.DefinicaoGrafico(ind.CUSTO, ind.TIPO, filtros={ind.PRAZO: "No prazo"},
                                     titulo="MEU GRÁFICO")
    assert ind.DefinicaoGrafico.de_json(definicao.para_json()) == definicao


# --------------------------------------------------------------------------- no banco
@pytest.fixture
def repo(tmp_path):
    with Repositorio.abrir(tmp_path / "calibracao.db", HOJE) as repositorio:
        yield repositorio


def test_painel_comeca_com_os_graficos_escolhidos_uma_vez_so(repo, tmp_path):
    graficos = repo.listar_graficos()
    assert [d.titulo for _, d in graficos] == [d.titulo for d in ind.PAINEL_INICIAL]
    for grafico_id, _ in graficos:
        repo.tirar_grafico(grafico_id)
    repo.fechar()
    with Repositorio.abrir(tmp_path / "calibracao.db", HOJE) as de_novo:
        assert de_novo.listar_graficos() == []  # tirou todos: não volta sozinho


def test_incluir_alterar_tirar_e_voltar(repo):
    novo = repo.incluir_grafico(ind.DefinicaoGrafico(ind.CUSTO, ind.TIPO, titulo="X"))
    repo.alterar_grafico(novo, ind.DefinicaoGrafico(ind.CUSTO, ind.ANO, titulo="Y"))
    assert repo.obter_grafico(novo).titulo == "Y"
    repo.tirar_grafico(novo)
    assert novo not in [g for g, _ in repo.listar_graficos()]
    repo.voltar_grafico(novo)
    assert [g for g, _ in repo.listar_graficos()][-1] == novo  # volta para o mesmo lugar


def test_modo_consulta_nao_mexe_no_painel(repo):
    repo.modo_consulta = True
    with pytest.raises(Exception, match="consulta"):
        repo.incluir_grafico(ind.DefinicaoGrafico())


def test_dados_dos_indicadores_do_banco(repo):
    plano = repo.incluir_plano(Plano("Plano PAQ-900"))
    ponto_id = repo.incluir_ponto(PontoPlano(plano, "NUMERICO", "50", valor_nominal=50.0,
                                             unidade="mm", tolerancia_inferior=-0.05,
                                             tolerancia_superior=0.05, incerteza=0.01))
    instrumento = repo.incluir_instrumento(Instrumento(
        "PAQ-900", "Paquímetro", localizacao="Usinagem / CT-01 - Reserva",
        periodicidade_meses=12, plano_id=plano, primeira_prevista=date(2027, 8, 10)))
    repo.registrar_calibracao(NovaCalibracao(
        instrumento, date(2027, 9, 15), [PontoMedido(ponto_id, valor=50.03, incerteza=0.01)],
        parecer_final=ParecerFinal.APROVADO, laboratorio="Lab A", custo=180.0), HOJE)
    calibracoes, instrumentos = repo.dados_dos_indicadores()
    [c] = calibracoes
    assert (c.prazo, c.limite, c.custo, c.laboratorio, c.locais) == (
        ind.COM_ATRASO_TXT, 80.0, 180.0, "Lab A", ["Usinagem", "CT-01"])
    assert [i.codigo for i in instrumentos] == ["PAQ-900"]


def test_sem_laboratorio_e_sem_custo(repo):
    plano = repo.incluir_plano(Plano("Plano TRE-900"))
    ponto_id = repo.incluir_ponto(PontoPlano(plano, "VERIFICACAO", "Aspecto"))
    instrumento = repo.incluir_instrumento(Instrumento("TRE-900", "Trena",
                                                       periodicidade_meses=12, plano_id=plano))
    repo.registrar_calibracao(NovaCalibracao(
        instrumento, date(2027, 10, 1), [PontoMedido(ponto_id, escolha=Resultado.APROVADO)],
        parecer_final=ParecerFinal.APROVADO), HOJE)
    [c], _ = repo.dados_dos_indicadores()
    assert (c.laboratorio, c.custo, c.limite, c.prazo) == (ind.SEM_LABORATORIO, 0.0, None,
                                                           ind.NO_PRAZO_TXT)


def test_agora_do_grafico_e_guardado(repo):
    grafico = repo.incluir_grafico(ind.DefinicaoGrafico(), datetime.datetime(2027, 1, 2, 3, 4))
    assert grafico > 0
