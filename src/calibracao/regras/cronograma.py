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
from dataclasses import dataclass
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


# --- Cronograma de qualquer mês (pedido do usuário em 2026-10-30) -------------------------
# Seletor de 12 meses para trás a 24 para a frente (como o protótipo): também limita a projeção.
MESES_PARA_TRAS = 12
MESES_PARA_FRENTE = 24


class SituacaoNoMes(StrEnum):
    FEITA = "Feita"
    PENDENTE = "Pendente este mês"
    VENCIDA = "Vencida"
    PREVISTA = "Prevista"


@dataclass(frozen=True)
class CalibracaoResumo:
    """O que o cronograma precisa de cada calibração (da mais antiga para a mais recente)."""

    data: datetime.date
    proxima: datetime.date | None  # a prevista a partir desta calibração
    custo: float | None = None
    motivo_atraso: str | None = None


@dataclass(frozen=True)
class PrevistaNoMes:
    prevista: datetime.date
    situacao: SituacaoNoMes
    realizada: datetime.date | None = None
    # Feita: o custo dela; não feita: o da última calibração com custo (estimativa; sem custo
    # registrado — ex.: calibração interna — fica None e conta como zero).
    custo: float | None = None
    motivo_atraso: str | None = None


def meses_do_seletor(hoje: datetime.date) -> list[datetime.date]:
    """Primeiro dia de cada mês do seletor, do mais antigo ao mais distante."""
    inicio = hoje.replace(day=1)
    return [somar_meses(inicio, n) for n in range(-MESES_PARA_TRAS, MESES_PARA_FRENTE + 1)]


def previstas_no_mes(calibracoes: list[CalibracaoResumo], periodicidade_meses: int | None,
                     mes: datetime.date, hoje: datetime.date,
                     ativo: bool = True) -> list[PrevistaNoMes]:
    """Calibrações previstas para o mês de `mes` de um instrumento.

    - Prevista de uma calibração que já teve a seguinte registrada → "Feita" (com a data em que foi
      feita, mesmo que depois do mês: o atraso não é alardeado, só guarda o motivo).
    - A prevista em aberto (depois da última calibração) → Vencida (mês já terminou), Pendente este
      mês ou Prevista.
    - Meses depois dela: projeção repetindo a periodicidade, só de este mês em diante.
    Instrumento desativado (`ativo=False`) mostra só o que já foi feito.
    """
    if not calibracoes:
        return []
    este_mes = hoje.replace(day=1)
    custos = [c.custo for c in calibracoes if c.custo is not None]
    ultimo_custo = custos[-1] if custos else None
    resultado = []
    for anterior, seguinte in zip(calibracoes, calibracoes[1:], strict=False):
        if mesmo_mes(anterior.proxima, mes):
            resultado.append(PrevistaNoMes(anterior.proxima, SituacaoNoMes.FEITA, seguinte.data,
                                           seguinte.custo, seguinte.motivo_atraso))
    aberta = calibracoes[-1].proxima
    if not ativo or aberta is None:
        return resultado
    if mesmo_mes(aberta, mes):
        if mes < este_mes:
            situacao_aberta = SituacaoNoMes.VENCIDA
        elif mes == este_mes:
            situacao_aberta = SituacaoNoMes.PENDENTE
        else:
            situacao_aberta = SituacaoNoMes.PREVISTA
        resultado.append(PrevistaNoMes(aberta, situacao_aberta, custo=ultimo_custo))
    elif periodicidade_meses and mes >= este_mes:
        limite = somar_meses(este_mes, MESES_PARA_FRENTE + 1)
        vezes = 1
        projetada = somar_meses(aberta, periodicidade_meses)
        while projetada < limite and projetada < somar_meses(mes, 1):
            if mesmo_mes(projetada, mes):
                resultado.append(PrevistaNoMes(projetada, SituacaoNoMes.PREVISTA,
                                               custo=ultimo_custo))
            vezes += 1
            projetada = somar_meses(aberta, periodicidade_meses * vezes)
    return resultado
