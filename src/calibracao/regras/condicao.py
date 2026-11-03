"""Condição do instrumento e parecer final da calibração (decisões do usuário em 2026-10-29).

Cada calibração tem o resultado automático (pelos pontos) e o parecer final, escolhido por quem
analisa — como no protótipo. O parecer muda a condição do instrumento; a mudança fica no histórico
("desativado em X").

Orientação indicativa NÃO é condição (pedido do usuário em 2026-11-03): é uma marca a mais, como a
Reserva — o instrumento pode estar Em uso e ser orientação indicativa. A marca fica na localização
(" - Orientação indicativa", ver `regras/localizacao.py`); o parecer "Orientação indicativa" deixa
o instrumento Em uso e põe a marca.
"""

import datetime
from enum import StrEnum

from calibracao.regras.avaliacao import Resultado


class Condicao(StrEnum):
    EM_USO = "Em uso"
    DESATIVADO = "Desativado"  # sai do cronograma


class ParecerFinal(StrEnum):
    APROVADO = "Aprovado"
    ORIENTACAO_INDICATIVA = "Orientação indicativa"
    REPROVADO_DESATIVADO = "Reprovado - Desativado"


CONDICAO_DO_PARECER = {
    ParecerFinal.APROVADO: Condicao.EM_USO,
    ParecerFinal.ORIENTACAO_INDICATIVA: Condicao.EM_USO,  # e põe a marca na localização
    ParecerFinal.REPROVADO_DESATIVADO: Condicao.DESATIVADO,
}


def pareceres_permitidos(resultado_automatico: Resultado) -> list[ParecerFinal]:
    """Reprovado pelos pontos não pode receber parecer "Aprovado"."""
    if resultado_automatico == Resultado.REPROVADO:
        return [ParecerFinal.ORIENTACAO_INDICATIVA, ParecerFinal.REPROVADO_DESATIVADO]
    return list(ParecerFinal)


def parecer_sugerido(resultado_automatico: Resultado) -> ParecerFinal:
    return pareceres_permitidos(resultado_automatico)[0]


def erros_mudanca_condicao(data: datetime.date | None, hoje: datetime.date) -> list[str]:
    """Data obrigatória e não futura; motivo/observação é opcional."""
    if data is None:
        return ["Informe a data."]
    if data > hoje:
        return ["A data não pode ser no futuro."]
    return []
