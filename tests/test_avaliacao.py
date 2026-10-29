"""Avaliação dos pontos numéricos e de limite, considerando a incerteza U."""

import pytest

from calibracao.regras.avaliacao import (
    Resultado,
    avaliar_limite,
    avaliar_numerico,
    pode_salvar,
    resultado_geral,
)

A = Resultado.APROVADO
R = Resultado.REPROVADO
NA = Resultado.NAO_APLICAVEL


def numerico(valor, nominal=60.0, tol=0.05, incerteza=0.01):
    return avaliar_numerico(valor, nominal=nominal, tolerancia_inferior=-tol,
                            tolerancia_superior=tol, incerteza=incerteza)


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [
        (60.00, Resultado.APROVADO),
        (60.04, Resultado.APROVADO),   # 0,04 + 0,01 = 0,05: encosta no limite, ainda aprovado
        (60.045, Resultado.REPROVADO),  # medido dentro, mas a faixa com U passa de 0,05
        (59.96, Resultado.APROVADO),
        (59.955, Resultado.REPROVADO),
    ],
)
def test_numerico_com_nominal(valor, esperado):
    assert numerico(valor).resultado == esperado


def test_limite_exato_nao_reprova_por_arredondamento():
    # 1,15 − 1,1 dá 0,04999…98 no computador; com U = 0 deve continuar aprovado.
    assert numerico(1.15, nominal=1.1, incerteza=0.0).resultado == Resultado.APROVADO


def test_incerteza_ausente_nunca_vale_zero():
    avaliacao = numerico(60.0, incerteza=None)
    assert avaliacao.resultado == Resultado.NAO_AVALIADO
    assert avaliacao.motivo == "incerteza ausente"


def test_incerteza_negativa_usada_sem_sinal():
    assert numerico(60.045, incerteza=-0.01).resultado == Resultado.REPROVADO
    assert numerico(60.0, incerteza=-0.01).faixa == pytest.approx((-0.01, 0.01))


def test_valor_nao_informado():
    assert numerico(None).resultado == Resultado.NAO_INFORMADO


def test_sem_tolerancia_nao_avalia():
    avaliacao = avaliar_numerico(1.0, nominal=1.0, tolerancia_inferior=None,
                                 tolerancia_superior=None, incerteza=0.1)
    assert (avaliacao.resultado, avaliacao.motivo) == (Resultado.NAO_AVALIADO, "tolerância ausente")


@pytest.mark.parametrize(
    ("erro", "esperado"),
    [(0.8, Resultado.APROVADO), (2.9, Resultado.REPROVADO), (-2.9, Resultado.REPROVADO)],
)
def test_sem_nominal_fixo_usa_o_erro_do_certificado(erro, esperado):
    # Durômetro, 1º ponto HR15T: ± 3,0 com U = 0,33 (exemplo combinado com o usuário).
    assert numerico(erro, nominal=None, tol=3.0, incerteza=0.33).resultado == esperado


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [(1.5, Resultado.APROVADO), (1.8, Resultado.REPROVADO), (2.0, Resultado.REPROVADO)],
)
def test_limite_maximo(valor, esperado):
    # Planeza: 2 µm máx, U = 0,3 → aprovado só se medido + U ≤ 2.
    assert avaliar_limite(valor, minimo=None, maximo=2.0, incerteza=0.3).resultado == esperado


@pytest.mark.parametrize(
    ("valor", "esperado"),
    [(650.0, Resultado.APROVADO), (630.0, Resultado.REPROVADO)],
)
def test_limite_minimo(valor, esperado):
    # Resistência do nó: mín. 628 MPa, U = 5 → aprovado só se medido − U ≥ 628.
    assert avaliar_limite(valor, minimo=628.0, maximo=None, incerteza=5.0).resultado == esperado


def test_limite_sem_incerteza_nao_avalia():
    avaliacao = avaliar_limite(1.0, minimo=None, maximo=2.0, incerteza=None)
    assert avaliacao.resultado == Resultado.NAO_AVALIADO


@pytest.mark.parametrize(
    ("resultados", "esperado"),
    [
        ([A, A, A], A),
        ([A, R, A], R),
        ([A, NA, A], A),                    # não aplicável não conta
        ([NA, NA], Resultado.PENDENTE),      # nenhum ponto avaliado
        ([A, Resultado.NAO_INFORMADO], Resultado.PENDENTE),  # ponto em branco nunca é ignorado
        ([R, Resultado.NAO_AVALIADO], Resultado.PENDENTE),   # sem U: não dá para fechar
        ([], Resultado.PENDENTE),
    ],
)
def test_resultado_geral(resultados, esperado):
    assert resultado_geral(resultados) == esperado


def test_so_salva_sem_pendencia():
    assert pode_salvar([A, NA, R])
    assert not pode_salvar([A, Resultado.NAO_INFORMADO])
