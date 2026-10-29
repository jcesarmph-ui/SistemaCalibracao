"""Cronograma por mês (como a MG acompanha: as calibrações do mês, do dia 1 ao 31).

Decisões do usuário em 2026-10-29:
- Próxima calibração = data da última calibração + periodicidade em meses.
- Previsto para este mês e ainda não feito → "Pendente este mês" até o dia 31; só vira "Vencida"
  a partir do dia 1º do mês seguinte.
- Previsto para este mês e já calibrado neste mês → "Feita este mês" (conta no total do mês).
- Previsto para o mês seguinte → "Próximo mês". Depois disso → "Em dia".
- O programa começa sem calibrações: até a primeira, o instrumento fica em "Sem calibração no
  programa" (transição da planilha).
"""

import calendar
import datetime
from enum import StrEnum


class Situacao(StrEnum):
    VENCIDA = "Vencida"
    PENDENTE_MES = "Pendente este mês"
    FEITA_MES = "Feita este mês"
    PROXIMO_MES = "Próximo mês"
    EM_DIA = "Em dia"
    SEM_CALIBRACAO = "Sem calibração no programa"
    SEM_PERIODICIDADE = "Sem periodicidade"


def somar_meses(data: datetime.date, meses: int) -> datetime.date:
    """Soma meses no calendário; dia inexistente no mês final vira o último (31/01 + 1 = 28/02)."""
    indice = data.month - 1 + meses
    ano, mes = data.year + indice // 12, indice % 12 + 1
    return datetime.date(ano, mes, min(data.day, calendar.monthrange(ano, mes)[1]))


def proxima_calibracao(ultima: datetime.date | None,
                       periodicidade_meses: int | None) -> datetime.date | None:
    if ultima is None or not periodicidade_meses:
        return None
    return somar_meses(ultima, periodicidade_meses)


def mesmo_mes(data: datetime.date | None, referencia: datetime.date) -> bool:
    return data is not None and (data.year, data.month) == (referencia.year, referencia.month)


def situacao(ultima: datetime.date | None, proxima: datetime.date | None,
             hoje: datetime.date, prevista_anterior: datetime.date | None = None) -> Situacao:
    """Situação do instrumento.

    `ultima`: data da última calibração **visível** (fora da Lixeira); `proxima`: a data prevista a
    partir dela; `prevista_anterior`: a data que estava prevista antes dessa última calibração (para
    saber se ela foi a calibração prevista para este mês).
    """
    if ultima is None:
        return Situacao.SEM_CALIBRACAO
    if mesmo_mes(ultima, hoje) and mesmo_mes(prevista_anterior, hoje):
        return Situacao.FEITA_MES
    if proxima is None:
        return Situacao.SEM_PERIODICIDADE
    if proxima < hoje.replace(day=1):
        return Situacao.VENCIDA
    if mesmo_mes(proxima, hoje):
        return Situacao.PENDENTE_MES
    if mesmo_mes(proxima, somar_meses(hoje.replace(day=1), 1)):
        return Situacao.PROXIMO_MES
    return Situacao.EM_DIA


def previsto_no_mes(proxima: datetime.date | None, ano: int, mes: int) -> bool:
    return proxima is not None and (proxima.year, proxima.month) == (ano, mes)
