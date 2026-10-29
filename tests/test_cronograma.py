"""Cronograma: próxima calibração e situação de cada instrumento."""

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
    ("ultima", "esperado"),
    [
        (date(2026, 3, 14), Situacao.VENCIDA),           # venceu ontem
        (date(2026, 3, 15), Situacao.PROXIMOS_30_DIAS),  # vence hoje: ainda não está vencida
        (date(2026, 4, 14), Situacao.PROXIMOS_30_DIAS),  # vence daqui a 30 dias
        (date(2026, 4, 15), Situacao.EM_DIA),            # 31 dias
        (None, Situacao.SEM_CALIBRACAO),                 # transição: nunca calibrado no programa
    ],
)
def test_situacao(ultima, esperado):
    assert situacao(ultima, 12, HOJE) == esperado


def test_sem_periodicidade():
    assert situacao(date(2027, 1, 1), None, HOJE) == Situacao.SEM_PERIODICIDADE


def test_previsto_no_mes():
    assert previsto_no_mes(date(2027, 3, 31), 2027, 3)
    assert not previsto_no_mes(date(2027, 4, 1), 2027, 3)
    assert not previsto_no_mes(date(2028, 3, 1), 2027, 3)
    assert not previsto_no_mes(None, 2027, 3)
