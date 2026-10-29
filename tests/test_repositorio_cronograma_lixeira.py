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
from calibracao.regras.cronograma import Situacao
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


def calibrar(repo, instrumento_id, data):
    [ponto] = repo.listar_pontos(repo.obter_instrumento(instrumento_id).plano_id)
    return repo.registrar_calibracao(NovaCalibracao(instrumento_id, data, [
        PontoMedido(ponto.id, escolha=Resultado.APROVADO)]), HOJE)


def situacoes(repo):
    return {linha.instrumento.codigo: linha.situacao for linha in repo.cronograma(HOJE)}


# ---------------------------------------------------------------- cronograma

def test_cronograma_com_cada_situacao(repo):
    calibrar(repo, novo_instrumento(repo, "A-VENCIDA"), date(2026, 3, 1))
    calibrar(repo, novo_instrumento(repo, "B-PROXIMA"), date(2026, 4, 1))
    calibrar(repo, novo_instrumento(repo, "C-EM-DIA"), date(2027, 1, 1))
    novo_instrumento(repo, "D-NOVO")
    assert situacoes(repo) == {
        "A-VENCIDA": Situacao.VENCIDA,
        "B-PROXIMA": Situacao.PROXIMOS_30_DIAS,
        "C-EM-DIA": Situacao.EM_DIA,
        "D-NOVO": Situacao.SEM_CALIBRACAO,
    }


def test_cronograma_usa_a_ultima_calibracao(repo):
    a = novo_instrumento(repo, "A")
    calibrar(repo, a, date(2026, 3, 1))
    calibrar(repo, a, date(2027, 3, 1))
    [linha] = repo.cronograma(HOJE)
    assert (linha.ultima, linha.proxima, linha.situacao) == (
        date(2027, 3, 1), date(2028, 3, 1), Situacao.EM_DIA)


def test_cronograma_ignora_desativados_e_quem_nao_precisa(repo):
    novo_instrumento(repo, "A")
    desativado = novo_instrumento(repo, "B")
    repo.desativar_instrumento(desativado, HOJE, "Perdido", HOJE)
    novo_instrumento(repo, "C", exige_calibracao=False)
    assert list(situacoes(repo)) == ["A"]


def test_calibracao_na_lixeira_nao_conta_no_cronograma(repo):
    a = novo_instrumento(repo, "A")
    calibrar(repo, a, date(2026, 3, 1))
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
