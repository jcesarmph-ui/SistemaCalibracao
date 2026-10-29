"""Regras da lixeira e da desativação de instrumentos (programa novo)."""

from datetime import date

import pytest

from calibracao.regras.lixeira import (
    Tipo,
    bloqueio_exclusao_permanente,
    bloqueio_restaurar,
    erros_desativacao,
)

HOJE = date(2027, 3, 15)


def test_restaurar_exige_pai_ativo():
    assert bloqueio_restaurar(Tipo.PONTO, pai_na_lixeira=False) is None
    assert "plano" in bloqueio_restaurar(Tipo.PONTO, pai_na_lixeira=True)
    assert "instrumento" in bloqueio_restaurar(Tipo.CALIBRACAO, pai_na_lixeira=True)


@pytest.mark.parametrize("confirmacao", ["", "excluir", "EXCLUI", "SIM"])
def test_exclusao_permanente_exige_digitar_excluir(confirmacao):
    assert bloqueio_exclusao_permanente(Tipo.PONTO, confirmacao, tem_dependencias=False)


def test_exclusao_permanente_aceita_espacos_em_volta():
    assert bloqueio_exclusao_permanente(Tipo.PONTO, " EXCLUIR ", tem_dependencias=False) is None


@pytest.mark.parametrize("tipo", [Tipo.INSTRUMENTO, Tipo.PLANO, Tipo.PONTO])
def test_exclusao_permanente_bloqueada_com_dependencias(tipo):
    assert bloqueio_exclusao_permanente(tipo, "EXCLUIR", tem_dependencias=True)


def test_calibracao_pode_ser_apagada_de_vez():
    # Decisão do usuário: calibração registrada por engano pode sair de vez (com os pontos medidos).
    assert bloqueio_exclusao_permanente(Tipo.CALIBRACAO, "EXCLUIR", tem_dependencias=True) is None


def test_desativacao_valida():
    assert erros_desativacao("Quebrou", HOJE, HOJE) == []


@pytest.mark.parametrize(
    ("motivo", "data", "erro"),
    [
        ("", HOJE, "motivo"),
        ("   ", HOJE, "motivo"),
        ("Quebrou", None, "data"),
        ("Quebrou", date(2027, 3, 16), "futuro"),
    ],
)
def test_desativacao_invalida(motivo, data, erro):
    assert any(erro in e for e in erros_desativacao(motivo, data, HOJE))
