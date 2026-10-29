"""Condição do instrumento e parecer final da calibração."""

from datetime import date

from calibracao.regras.avaliacao import Resultado
from calibracao.regras.condicao import (
    CONDICAO_DO_PARECER,
    Condicao,
    ParecerFinal,
    erros_mudanca_condicao,
    parecer_sugerido,
    pareceres_permitidos,
)

HOJE = date(2027, 3, 15)


def test_aprovado_pode_receber_qualquer_parecer():
    assert pareceres_permitidos(Resultado.APROVADO) == list(ParecerFinal)
    assert parecer_sugerido(Resultado.APROVADO) == ParecerFinal.APROVADO


def test_reprovado_nao_pode_ser_aprovado():
    permitidos = pareceres_permitidos(Resultado.REPROVADO)
    assert ParecerFinal.APROVADO not in permitidos
    assert parecer_sugerido(Resultado.REPROVADO) == ParecerFinal.ORIENTACAO_INDICATIVA


def test_parecer_muda_a_condicao():
    assert CONDICAO_DO_PARECER[ParecerFinal.APROVADO] == Condicao.EM_USO
    assert CONDICAO_DO_PARECER[ParecerFinal.ORIENTACAO_INDICATIVA] == \
        Condicao.ORIENTACAO_INDICATIVA
    assert CONDICAO_DO_PARECER[ParecerFinal.REPROVADO_DESATIVADO] == Condicao.DESATIVADO


def test_data_da_mudanca():
    assert erros_mudanca_condicao(HOJE, HOJE) == []
    assert erros_mudanca_condicao(None, HOJE) == ["Informe a data."]
    assert "futuro" in erros_mudanca_condicao(date(2027, 3, 16), HOJE)[0]
