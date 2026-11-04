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


def test_incerteza_nao_se_aplica_avalia_so_pelo_valor():
    """"-" ou "N/A" na DQ05 (pedido de 2026-11-03): sem U, mas avaliado."""


    assert avaliar_limite(0.64, minimo=None, maximo=2.0, incerteza=None,
                          sem_incerteza=True).resultado == Resultado.APROVADO
    assert avaliar_limite(2.1, minimo=None, maximo=2.0, incerteza=None,
                          sem_incerteza=True).resultado == Resultado.REPROVADO
    assert avaliar_numerico(1.04, nominal=1.0, tolerancia_inferior=-0.05,
                            tolerancia_superior=0.05, incerteza=None,
                            sem_incerteza=True).resultado == Resultado.APROVADO
    # sem a marca, U ausente continua "não avaliado" (nunca vira zero)
    assert avaliar_limite(0.64, minimo=None, maximo=2.0,
                          incerteza=None).resultado == Resultado.NAO_AVALIADO


def test_desvio_final_fica_do_lado_mais_perto_da_tolerancia():
    """Pedido de 2026-11-04: desvio −0,2 com U 0,1 e tolerância ± 0,5 → −0,3."""
    from calibracao.regras.avaliacao import DesvioFinal, desvio_final
    assert desvio_final(-0.2, 0.1, -0.5, 0.5).valor == pytest.approx(-0.3)
    assert desvio_final(0.2, 0.1, -0.5, 0.5).valor == pytest.approx(0.3)
    # tolerância de um lado só (ex.: -0,1 a +0,5): perto do lado de baixo
    assert desvio_final(0.05, 0.1, -0.1, 0.5).valor == pytest.approx(-0.05)
    # desvio zero com tolerância igual dos dois lados: "± U"
    assert desvio_final(0.0, 0.1, -0.5, 0.5) == DesvioFinal(0.1, dos_dois_lados=True)
    # U negativa vale sem o sinal
    assert desvio_final(-0.2, -0.1, -0.5, 0.5).valor == pytest.approx(-0.3)


def test_desvio_final_no_limite_e_sem_u():
    from calibracao.regras.avaliacao import desvio_final
    # limite "2 máx.": encontrado 1,8 e U 0,1 → 1,9
    assert desvio_final(1.8, 0.1, None, 2.0).valor == pytest.approx(1.9)
    assert desvio_final(700, 5, 628, None).valor == pytest.approx(695)
    # U ausente: nada (nunca U = 0); U não se aplica: o próprio desvio
    assert desvio_final(-0.2, None, -0.5, 0.5) is None
    assert desvio_final(-0.2, None, -0.5, 0.5, sem_incerteza=True).valor == -0.2
    assert desvio_final(None, 0.1, -0.5, 0.5) is None
