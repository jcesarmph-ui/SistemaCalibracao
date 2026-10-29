"""Cronograma por mês: próxima calibração e situação de cada instrumento."""

from datetime import date

import pytest

from calibracao.regras.cronograma import (
    Situacao,
    previsto_no_mes,
    proxima_calibracao,
    situacao,
    somar_meses,
)

HOJE = date(2027, 3, 15)


@pytest.mark.parametrize(
    ("data", "meses", "esperado"),
    [
        (date(2027, 3, 10), 12, date(2028, 3, 10)),
        (date(2027, 11, 20), 3, date(2028, 2, 20)),   # vira o ano
        (date(2027, 1, 31), 1, date(2027, 2, 28)),    # fevereiro não tem dia 31
        (date(2027, 2, 28), 24, date(2029, 2, 28)),
        (date(2028, 2, 29), 12, date(2029, 2, 28)),   # ano bissexto → ano comum
    ],
)
def test_somar_meses(data, meses, esperado):
    assert somar_meses(data, meses) == esperado


def test_proxima_sem_dados():
    assert proxima_calibracao(None, 12) is None
    assert proxima_calibracao(date(2027, 1, 1), None) is None


@pytest.mark.parametrize(
    ("proxima", "esperado"),
    [
        (date(2027, 2, 28), Situacao.VENCIDA),         # mês passado e não foi feito
        (date(2027, 3, 1), Situacao.PENDENTE_MES),     # já passou o dia, mas o mês não acabou
        (date(2027, 3, 31), Situacao.PENDENTE_MES),
        (date(2027, 4, 1), Situacao.PROXIMO_MES),
        (date(2027, 4, 30), Situacao.PROXIMO_MES),
        (date(2027, 5, 1), Situacao.EM_DIA),
    ],
)
def test_situacao_por_mes(proxima, esperado):
    assert situacao(date(2026, 3, 1), proxima, HOJE) == esperado


def test_pendente_so_vira_vencida_no_mes_seguinte():
    prevista = date(2027, 3, 10)
    assert situacao(date(2026, 3, 10), prevista, date(2027, 3, 31)) == Situacao.PENDENTE_MES
    assert situacao(date(2026, 3, 10), prevista, date(2027, 4, 1)) == Situacao.VENCIDA


def test_feita_este_mes():
    # Estava prevista para 10/03; calibrada em 05/03 → próxima em 2028.
    assert situacao(date(2027, 3, 5), date(2028, 3, 5), HOJE,
                    prevista_anterior=date(2027, 3, 10)) == Situacao.FEITA_MES


def test_vencida_de_mes_anterior_feita_agora_fica_em_dia():
    # Estava prevista para fevereiro (vencida); calibrada em março: não entra no total de março.
    assert situacao(date(2027, 3, 5), date(2028, 3, 5), HOJE,
                    prevista_anterior=date(2027, 2, 10)) == Situacao.EM_DIA


def test_primeira_calibracao_no_programa_fica_em_dia():
    assert situacao(date(2027, 3, 5), date(2028, 3, 5), HOJE) == Situacao.EM_DIA


def test_sem_calibracao_e_sem_periodicidade():
    assert situacao(None, None, HOJE) == Situacao.SEM_CALIBRACAO
    assert situacao(date(2027, 1, 1), None, HOJE) == Situacao.SEM_PERIODICIDADE


def test_virada_de_ano():
    assert situacao(date(2026, 1, 5), date(2028, 1, 5), date(2027, 12, 20)) == Situacao.PROXIMO_MES


def test_previsto_no_mes():
    assert previsto_no_mes(date(2027, 3, 31), 2027, 3)
    assert not previsto_no_mes(date(2027, 4, 1), 2027, 3)
    assert not previsto_no_mes(date(2028, 3, 1), 2027, 3)
    assert not previsto_no_mes(None, 2027, 3)
