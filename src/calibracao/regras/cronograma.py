"""Cronograma: próxima calibração e situação de cada instrumento (regras do protótipo).

- Próxima calibração = data da última calibração + periodicidade em meses.
- Vencida: a data prevista já passou (no próprio dia ainda não está vencida).
- Próximos 30 dias: vence de hoje até hoje + 30 dias.
- O programa começa sem calibrações: até a primeira, o instrumento fica em "Sem calibração no
  programa" (transição da planilha; o grupo diminui conforme as calibrações são registradas).
"""

import calendar
import datetime
from enum import StrEnum

DIAS_PROXIMOS = 30


class Situacao(StrEnum):
    VENCIDA = "Vencida"
    PROXIMOS_30_DIAS = "Próximos 30 dias"
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


def situacao(ultima: datetime.date | None, periodicidade_meses: int | None,
             hoje: datetime.date) -> Situacao:
    """`ultima` é a data da última calibração **visível** (fora da lixeira)."""
    if ultima is None:
        return Situacao.SEM_CALIBRACAO
    proxima = proxima_calibracao(ultima, periodicidade_meses)
    if proxima is None:
        return Situacao.SEM_PERIODICIDADE
    if proxima < hoje:
        return Situacao.VENCIDA
    if proxima <= hoje + datetime.timedelta(days=DIAS_PROXIMOS):
        return Situacao.PROXIMOS_30_DIAS
    return Situacao.EM_DIA


def previsto_no_mes(proxima: datetime.date | None, ano: int, mes: int) -> bool:
    return proxima is not None and (proxima.year, proxima.month) == (ano, mes)
