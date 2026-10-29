"""Repositório: planos de calibração e seus pontos."""

from datetime import date

import pytest

from calibracao.dados.repositorio import ErroDeValidacao, Plano, PontoPlano, Repositorio


@pytest.fixture
def repo(tmp_path):
    with Repositorio.abrir(tmp_path / "calibracao.db", date(2027, 3, 15)) as repositorio:
        yield repositorio


def numerico(plano_id, nominal, **outros):
    return PontoPlano(plano_id, "NUMERICO", f"{nominal}", valor_nominal=nominal,
                      tolerancia_inferior=-0.5, tolerancia_superior=0.5, **outros)


def test_incluir_plano_e_pontos_em_ordem(repo):
    plano = repo.incluir_plano(Plano("Plano TRE-901"))
    for nominal in (300.0, 900.0, 1500.0):
        repo.incluir_ponto(numerico(plano, nominal))
    pontos = repo.listar_pontos(plano)
    assert [(p.ordem, p.valor_nominal) for p in pontos] == [(1, 300.0), (2, 900.0), (3, 1500.0)]
    assert [p.nome for p in repo.listar_planos()] == ["Plano TRE-901"]


def test_preencher_a_incerteza_que_faltava(repo):
    # Caso real: as trenas vieram da planilha sem U; o usuário preenche pela edição do plano.
    plano = repo.incluir_plano(Plano("Plano TRE-901"))
    ponto_id = repo.incluir_ponto(numerico(plano, 300.0))
    [ponto] = repo.listar_pontos(plano)
    assert ponto.incerteza is None
    ponto.incerteza = 0.2
    repo.atualizar_ponto(ponto)
    assert repo.listar_pontos(plano)[0].incerteza == 0.2
    assert repo.listar_pontos(plano)[0].id == ponto_id


def test_ponto_sem_tolerancia_e_aceito(repo):
    # Fiel à planilha: pode existir sem tolerância/U; só não é avaliado na calibração.
    plano = repo.incluir_plano(Plano("Plano X"))
    repo.incluir_ponto(PontoPlano(plano, "NUMERICO", "10", valor_nominal=10.0))


@pytest.mark.parametrize(
    ("ponto", "mensagem"),
    [
        (PontoPlano(1, "QUALQUER", "10"), "Tipo de ponto inválido"),
        (PontoPlano(1, "NUMERICO", "  "), "descrição"),
        (PontoPlano(1, "NUMERICO", "10", tolerancia_inferior=0.5, tolerancia_superior=-0.5),
         "tolerância inferior"),
        (PontoPlano(1, "LIMITE", "Nó", valor_minimo=700.0, valor_maximo=628.0), "mínimo"),
    ],
)
def test_ponto_invalido(repo, ponto, mensagem):
    repo.incluir_plano(Plano("Plano X"))
    with pytest.raises(ErroDeValidacao, match=mensagem):
        repo.incluir_ponto(ponto)


def test_plano_sem_nome(repo):
    with pytest.raises(ErroDeValidacao, match="nome do plano"):
        repo.incluir_plano(Plano("   "))
