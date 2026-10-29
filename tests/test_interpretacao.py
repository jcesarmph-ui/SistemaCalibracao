"""Interpretação do conteúdo das células da planilha DQ05."""

import datetime

import pytest

from calibracao.importacao.interpretacao import (
    interpretar_tolerancia,
    nominal_do_texto,
    texto_exibido,
)


@pytest.mark.parametrize(
    ("valor", "formato", "esperado"),
    [
        (0.007, '"± "0.000', "± 0,007"),  # micrômetros: número com "± " só na formatação
        ("± 0,05", "General", "± 0,05"),
        ("  Executa função ", "General", "Executa função"),
        (1.1, "General", "1,1"),
        (60, "0.00", "60,00"),
        (12, "General", "12"),
        (datetime.datetime(2023, 9, 5), "General", "2023-09-05"),
        ("   ", "General", None),
        (None, "General", None),
    ],
)
def test_texto_exibido(valor, formato, esperado):
    assert texto_exibido(valor, formato) == esperado


def test_tolerancia_mais_menos():
    tol = interpretar_tolerancia("± 0,05", "60")
    assert (tol.tipo, tol.tolerancia_inferior, tol.tolerancia_superior) == ("NUMERICO", -0.05, 0.05)
    assert tol.unidade is None


def test_tolerancia_mais_menos_sem_espaco_e_com_unidade():
    assert interpretar_tolerancia("±10", "2000").tolerancia_superior == 10
    tol = interpretar_tolerancia("± 0,25°", "30° (Q1)")
    assert (tol.tolerancia_superior, tol.unidade) == (0.25, "°")


def test_tolerancia_minimo_e_maximo():
    minimo = interpretar_tolerancia("Mín. 628 MPa", "Resistência a tração do nó")
    assert (minimo.tipo, minimo.valor_minimo, minimo.unidade) == ("LIMITE", 628, "MPa")
    maximo = interpretar_tolerancia("2µm máx", "Planeza")
    assert (maximo.tipo, maximo.valor_maximo, maximo.unidade) == ("LIMITE", 2, "µm")


@pytest.mark.parametrize("classe", ["1", "B"])
def test_classe_exigida(classe):
    tol = interpretar_tolerancia(classe, "Classificação (Classe)")
    assert (tol.tipo, tol.classe_exigida) == ("CLASSE", classe)


@pytest.mark.parametrize("texto", ["Executa função", "Não Exec. função", "OK", "N/A"])
def test_criterio_em_texto(texto):
    assert interpretar_tolerancia(texto, "Teste funcional").tipo == "CRITERIO"


@pytest.mark.parametrize(
    ("descricao", "esperado"),
    [
        ("30° (Q1)", 30),
        ("0º", 0),
        ("90°", 90),
        ("1º ponto 67 a 80 HR15T", None),  # ordinal do durômetro, não é nominal
        ("Diferença entre 5 pontos", None),
    ],
)
def test_nominal_do_texto(descricao, esperado):
    assert nominal_do_texto(descricao) == esperado
