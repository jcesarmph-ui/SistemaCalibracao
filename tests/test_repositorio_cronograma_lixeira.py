"""Repositório: cronograma e lixeira."""

from datetime import date, datetime

import pytest

from calibracao.dados.repositorio import (
    ErroDeValidacao,
    Instrumento,
    NovaCalibracao,
    Plano,
    PontoMedido,
    PontoPlano,
    Repositorio,
)
from calibracao.regras.avaliacao import Resultado
from calibracao.regras.condicao import Condicao, ParecerFinal
from calibracao.regras.cronograma import Situacao, SituacaoNoMes
from calibracao.regras.lixeira import Tipo

HOJE = date(2027, 3, 15)
AGORA = datetime(2027, 3, 15, 10, 0)


@pytest.fixture
def repo(tmp_path):
    with Repositorio.abrir(tmp_path / "calibracao.db", HOJE) as repositorio:
        yield repositorio


def novo_instrumento(repo, codigo, periodicidade=12, **outros):
    """Instrumento fictício com plano de 1 verificação visual (fácil de calibrar no teste)."""
    plano = repo.incluir_plano(Plano(f"Plano {codigo}"))
    repo.incluir_ponto(PontoPlano(plano, "VERIFICACAO", "Aspecto geral"))
    return repo.incluir_instrumento(Instrumento(codigo, "Trena", plano_id=plano,
                                                periodicidade_meses=periodicidade, **outros))


def calibrar(repo, instrumento_id, data, parecer=ParecerFinal.APROVADO):
    [ponto] = repo.listar_pontos(repo.obter_instrumento(instrumento_id).plano_id)
    return repo.registrar_calibracao(NovaCalibracao(instrumento_id, data, [
        PontoMedido(ponto.id, escolha=Resultado.APROVADO)], parecer_final=parecer), HOJE)


def situacoes(repo):
    return {linha.instrumento.codigo: linha.situacao for linha in repo.cronograma(HOJE)}


# ---------------------------------------------------------------- cronograma

def test_cronograma_com_cada_situacao(repo):
    # Hoje = 15/03/2027; periodicidade de 12 meses.
    calibrar(repo, novo_instrumento(repo, "A-VENCIDA"), date(2026, 2, 1))   # previsto fev/2027
    calibrar(repo, novo_instrumento(repo, "B-PENDENTE"), date(2026, 3, 20))  # previsto mar/2027
    calibrar(repo, novo_instrumento(repo, "C-PROXIMO"), date(2026, 4, 10))   # previsto abr/2027
    calibrar(repo, novo_instrumento(repo, "D-EM-DIA"), date(2027, 1, 1))
    feita = novo_instrumento(repo, "E-FEITA")
    calibrar(repo, feita, date(2026, 3, 10))  # previsto 10/03/2027…
    calibrar(repo, feita, date(2027, 3, 5))   # …e feito em 05/03/2027
    novo_instrumento(repo, "F-NOVO")
    assert situacoes(repo) == {
        "A-VENCIDA": Situacao.VENCIDA,
        "B-PENDENTE": Situacao.PENDENTE_MES,
        "C-PROXIMO": Situacao.PROXIMO_MES,
        "D-EM-DIA": Situacao.EM_DIA,
        "E-FEITA": Situacao.FEITA_MES,
        "F-NOVO": Situacao.SEM_CALIBRACAO,
    }


def test_cronograma_usa_a_ultima_calibracao(repo):
    a = novo_instrumento(repo, "A")
    calibrar(repo, a, date(2025, 6, 1))
    calibrar(repo, a, date(2026, 6, 1))
    [linha] = repo.cronograma(HOJE)
    assert (linha.ultima, linha.proxima, linha.situacao) == (
        date(2026, 6, 1), date(2027, 6, 1), Situacao.EM_DIA)


def test_cronograma_ignora_desativados_e_quem_nao_precisa(repo):
    novo_instrumento(repo, "A")
    desativado = novo_instrumento(repo, "B")
    repo.desativar_instrumento(desativado, HOJE, "Perdido", HOJE)
    novo_instrumento(repo, "C", exige_calibracao=False)
    assert list(situacoes(repo)) == ["A"]


def test_orientacao_indicativa_continua_no_cronograma(repo):
    a = novo_instrumento(repo, "A")
    calibrar(repo, a, date(2027, 3, 1), parecer=ParecerFinal.ORIENTACAO_INDICATIVA)
    [linha] = repo.cronograma(HOJE)
    assert (linha.condicao, linha.parecer_ultima, linha.situacao) == (
        Condicao.ORIENTACAO_INDICATIVA, ParecerFinal.ORIENTACAO_INDICATIVA, Situacao.EM_DIA)


def test_calibracao_na_lixeira_nao_conta_no_cronograma(repo):
    a = novo_instrumento(repo, "A")
    calibrar(repo, a, date(2026, 2, 1))
    engano = calibrar(repo, a, date(2027, 3, 1))
    repo.enviar_para_lixeira(Tipo.CALIBRACAO, engano, "Registrada no instrumento errado", AGORA)
    assert situacoes(repo)["A"] == Situacao.VENCIDA


# ---------------------------------------------------------------- lixeira

def test_lixeira_lista_e_restaura(repo):
    a = novo_instrumento(repo, "A")
    repo.enviar_para_lixeira(Tipo.INSTRUMENTO, a, "Cadastro duplicado", AGORA)
    assert repo.listar_instrumentos() == []
    [item] = repo.listar_lixeira()
    assert (item.tipo, item.descricao, item.motivo) == (
        Tipo.INSTRUMENTO, "A — Trena", "Cadastro duplicado")
    repo.restaurar(Tipo.INSTRUMENTO, a)
    assert [i.codigo for i in repo.listar_instrumentos()] == ["A"]
    assert repo.listar_lixeira() == []


def test_restaurar_exige_o_pai_ativo(repo):
    a = novo_instrumento(repo, "A")
    calibracao = calibrar(repo, a, date(2027, 3, 1))
    repo.enviar_para_lixeira(Tipo.CALIBRACAO, calibracao, None, AGORA)
    repo.enviar_para_lixeira(Tipo.INSTRUMENTO, a, None, AGORA)
    with pytest.raises(ErroDeValidacao, match="Restaure primeiro o instrumento"):
        repo.restaurar(Tipo.CALIBRACAO, calibracao)


def test_nao_registra_calibracao_em_instrumento_ou_plano_na_lixeira(repo):
    a = novo_instrumento(repo, "A")
    repo.enviar_para_lixeira(Tipo.PLANO, repo.obter_instrumento(a).plano_id, None, AGORA)
    with pytest.raises(ErroDeValidacao, match="plano deste instrumento está na Lixeira"):
        calibrar(repo, a, HOJE)


def test_calibracao_pode_ser_apagada_de_vez(repo):
    a = novo_instrumento(repo, "A")
    calibracao = calibrar(repo, a, HOJE)
    with pytest.raises(ErroDeValidacao, match="está na Lixeira"):
        repo.excluir_permanentemente(Tipo.CALIBRACAO, calibracao, "EXCLUIR")
    repo.enviar_para_lixeira(Tipo.CALIBRACAO, calibracao, "Engano", AGORA)
    with pytest.raises(ErroDeValidacao, match="digite EXCLUIR"):
        repo.excluir_permanentemente(Tipo.CALIBRACAO, calibracao, "sim")
    repo.excluir_permanentemente(Tipo.CALIBRACAO, calibracao, "EXCLUIR")
    assert repo.listar_lixeira() == []
    assert repo.pontos_da_calibracao(calibracao) == []


def test_instrumento_com_calibracoes_nao_e_apagado_de_vez(repo):
    a = novo_instrumento(repo, "A")
    calibrar(repo, a, HOJE)
    repo.enviar_para_lixeira(Tipo.INSTRUMENTO, a, None, AGORA)
    with pytest.raises(ErroDeValidacao, match="registros ligados"):
        repo.excluir_permanentemente(Tipo.INSTRUMENTO, a, "EXCLUIR")


def test_instrumento_sem_calibracoes_e_apagado_de_vez(repo):
    a = novo_instrumento(repo, "A")
    repo.desativar_instrumento(a, HOJE, "Perdido", HOJE)
    repo.enviar_para_lixeira(Tipo.INSTRUMENTO, a, "Cadastrado por engano", AGORA)
    repo.excluir_permanentemente(Tipo.INSTRUMENTO, a, "EXCLUIR")
    assert repo.listar_instrumentos(incluir_desativados=True) == []


# ---------------------------------------------------------------- cronograma de qualquer mês

def test_cronograma_de_um_mes_futuro_com_projecao(repo):
    a = novo_instrumento(repo, "A-ANUAL")
    calibrar(repo, a, date(2026, 6, 1))           # prevista jun/2027, depois jun/2028
    b = novo_instrumento(repo, "B-SEMESTRAL", periodicidade=6)
    calibrar(repo, b, date(2027, 1, 10))          # jul/2027, jan/2028, jul/2028…
    junho_2028 = [(linha.instrumento.codigo, linha.prevista.situacao)
                  for linha in repo.cronograma_do_mes(date(2028, 6, 1), HOJE)]
    assert junho_2028 == [("A-ANUAL", SituacaoNoMes.PREVISTA)]
    julho_2028 = [linha.instrumento.codigo
                  for linha in repo.cronograma_do_mes(date(2028, 7, 1), HOJE)]
    assert julho_2028 == ["B-SEMESTRAL"]


def test_cronograma_de_um_mes_passado_mostra_quando_foi_feita(repo):
    a = novo_instrumento(repo, "A")
    calibrar(repo, a, date(2025, 1, 10))  # prevista jan/2026…
    calibrar(repo, a, date(2026, 2, 3))   # …feita em fevereiro
    [linha] = repo.cronograma_do_mes(date(2026, 1, 1), HOJE)
    assert (linha.prevista.situacao, linha.prevista.realizada) == (
        SituacaoNoMes.FEITA, date(2026, 2, 3))


def test_motivo_do_atraso_da_vencida_vai_para_a_calibracao(repo):
    a = novo_instrumento(repo, "A")
    calibrar(repo, a, date(2026, 2, 1))  # vencida desde fev/2027
    repo.informar_motivo_atraso(a, "Aguardando orçamento")
    assert repo.motivos_atraso_pendentes() == {a: "Aguardando orçamento"}
    [linha] = [x for x in repo.cronograma(HOJE) if x.instrumento.id == a]
    assert linha.motivo_atraso == "Aguardando orçamento"
    [mes] = repo.cronograma_do_mes(date(2027, 2, 1), HOJE)
    assert mes.prevista.motivo_atraso == "Aguardando orçamento"
    assert repo.prevista_atual(a) == date(2027, 2, 1)
    # ao registrar, o motivo pendente some do instrumento
    [ponto] = repo.listar_pontos(repo.obter_instrumento(a).plano_id)
    repo.registrar_calibracao(NovaCalibracao(
        a, date(2027, 3, 10), [PontoMedido(ponto.id, escolha=Resultado.APROVADO)],
        parecer_final=ParecerFinal.APROVADO, motivo_atraso="Aguardando orçamento"), HOJE)
    assert repo.motivos_atraso_pendentes() == {}
    assert repo.listar_calibracoes(a)[-1].motivo_atraso == "Aguardando orçamento"
    [mes] = repo.cronograma_do_mes(date(2027, 2, 1), HOJE)
    assert (mes.prevista.situacao, mes.prevista.motivo_atraso) == (
        SituacaoNoMes.FEITA, "Aguardando orçamento")


def test_motivo_do_atraso_nao_grava_no_modo_consulta(repo):
    a = novo_instrumento(repo, "A")
    repo.modo_consulta = True
    with pytest.raises(ErroDeValidacao):
        repo.informar_motivo_atraso(a, "x")
