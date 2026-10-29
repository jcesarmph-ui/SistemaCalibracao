"""Avaliação dos pontos medidos, sempre considerando a incerteza de medição (U).

Regra (herdada do protótipo): o ponto só é aprovado se a faixa inteira `[x − U, x + U]` ficar dentro
dos limites. Incerteza ausente nunca vale zero: o ponto fica "não avaliado". U negativa (existe na
planilha DQ05) é usada sem o sinal.

- Numérico com nominal: x = medido − nominal, comparado com a tolerância (ex.: ± 0,05).
- Numérico sem nominal fixo (durômetro, excentricidade da balança): o laboratório já entrega o erro;
  x = o próprio erro digitado.
- Limite (ex.: "2 µm máx", "Mín. 628 MPa"): x = medido, comparado com o mínimo e/ou o máximo.
"""

from dataclasses import dataclass
from enum import StrEnum

# Folga para erros de arredondamento do ponto flutuante (ex.: 1,15 − 1,1 = 0,04999…98).
_FOLGA = 1e-9


class Resultado(StrEnum):
    APROVADO = "Aprovado"
    REPROVADO = "Reprovado"
    # Marcado pelo usuário, com motivo; não conta no resultado geral.
    NAO_APLICAVEL = "Não aplicável"
    NAO_INFORMADO = "Não informado"
    NAO_AVALIADO = "Não avaliado"
    # Só no resultado geral: falta preencher ou avaliar algum ponto.
    PENDENTE = "Pendente"


@dataclass(frozen=True)
class Avaliacao:
    resultado: Resultado
    motivo: str | None = None
    # Faixa avaliada [x − U, x + U] (x = erro no numérico, medido no limite), para tela e gráfico.
    faixa: tuple[float, float] | None = None


def _comparar(x: float, incerteza: float | None, minimo: float | None,
              maximo: float | None) -> Avaliacao:
    if incerteza is None:
        return Avaliacao(Resultado.NAO_AVALIADO, "incerteza ausente")
    if minimo is None and maximo is None:
        return Avaliacao(Resultado.NAO_AVALIADO, "tolerância ausente")
    u = abs(incerteza)
    faixa = (x - u, x + u)
    if minimo is not None and faixa[0] < minimo - _FOLGA:
        return Avaliacao(Resultado.REPROVADO, "abaixo do limite inferior", faixa)
    if maximo is not None and faixa[1] > maximo + _FOLGA:
        return Avaliacao(Resultado.REPROVADO, "acima do limite superior", faixa)
    return Avaliacao(Resultado.APROVADO, None, faixa)


def avaliar_numerico(valor: float | None, *, nominal: float | None,
                     tolerancia_inferior: float | None, tolerancia_superior: float | None,
                     incerteza: float | None) -> Avaliacao:
    """`valor` é o medido (com nominal) ou o erro do certificado (sem nominal fixo)."""
    if valor is None:
        return Avaliacao(Resultado.NAO_INFORMADO)
    erro = valor - nominal if nominal is not None else valor
    return _comparar(erro, incerteza, tolerancia_inferior, tolerancia_superior)


def avaliar_limite(valor: float | None, *, minimo: float | None, maximo: float | None,
                   incerteza: float | None) -> Avaliacao:
    if valor is None:
        return Avaliacao(Resultado.NAO_INFORMADO)
    return _comparar(valor, incerteza, minimo, maximo)


def resultado_geral(resultados: list[Resultado]) -> Resultado:
    """Resultado da calibração inteira a partir do resultado de cada ponto.

    Todo ponto precisa estar preenchido (ou marcado "não aplicável") para a calibração poder ser
    salva: ponto em branco ou sem avaliação deixa tudo "pendente" — nunca é ignorado.
    """
    if any(r in (Resultado.NAO_INFORMADO, Resultado.NAO_AVALIADO) for r in resultados):
        return Resultado.PENDENTE
    contam = [r for r in resultados if r != Resultado.NAO_APLICAVEL]
    if not contam:
        return Resultado.PENDENTE
    if Resultado.REPROVADO in contam:
        return Resultado.REPROVADO
    return Resultado.APROVADO


def pode_salvar(resultados: list[Resultado]) -> bool:
    return resultado_geral(resultados) != Resultado.PENDENTE
