"""Regras para interpretar o conteúdo das células da planilha DQ05.

Funções puras (sem Excel nem banco): recebem valores e devolvem o que o programa guarda. O dado vai
como está na planilha — aqui só se decide o *significado* (tolerância ±, mínimo, classe, critério…),
nunca se corrige valor.
"""

import datetime
import re
import unicodedata
from dataclasses import dataclass

NUMERO = r"(-?\d+(?:[.,]\d+)?)"


def para_numero(texto: str) -> float:
    return float(texto.replace(",", "."))


def normalizar(texto: object) -> str:
    """Maiúsculas, sem acentos e com espaços simples — só para comparar textos."""
    sem_acento = unicodedata.normalize("NFKD", str(texto or "")).encode("ascii", "ignore").decode()
    return re.sub(r"\s+", " ", sem_acento).strip().upper()


def texto_exibido(valor: object, formato: str = "General") -> str | None:
    """Texto como o Excel mostra a célula (ex.: 0.007 com formato `"± "0.000` → "± 0,007")."""
    if valor is None:
        return None
    if isinstance(valor, datetime.datetime):
        return valor.date().isoformat()
    if isinstance(valor, bool) or not isinstance(valor, int | float):
        texto = str(valor).strip()
        return texto or None
    prefixo = re.match(r'^"([^"]*)"', formato or "")
    casas = re.search(r"0\.(0+)", formato or "")
    if casas:
        numero = f"{valor:.{len(casas.group(1))}f}"
    else:
        numero = f"{valor:g}" if isinstance(valor, float) else str(valor)
    return (prefixo.group(1) if prefixo else "") + numero.replace(".", ",")


@dataclass
class Tolerancia:
    """Significado da coluna "Tolerância" de um ponto."""

    tipo: str  # NUMERICO, LIMITE, CLASSE ou CRITERIO
    tolerancia_inferior: float | None = None
    tolerancia_superior: float | None = None
    valor_minimo: float | None = None
    valor_maximo: float | None = None
    unidade: str | None = None
    classe_exigida: str | None = None


def interpretar_tolerancia(texto: str, descricao: str) -> Tolerancia:
    """Interpreta o texto exibido na coluna "Tolerância" (nunca vazio aqui)."""
    texto = texto.strip()
    if "CLASSE" in normalizar(descricao):
        return Tolerancia("CLASSE", classe_exigida=texto)

    mais_menos = re.fullmatch(rf"±\s*{NUMERO}\s*(\S*)", texto)
    if mais_menos:
        valor = abs(para_numero(mais_menos.group(1)))
        return Tolerancia("NUMERICO", -valor, valor, unidade=mais_menos.group(2) or None)

    minimo = re.fullmatch(rf"m[ií]n\.?\s*{NUMERO}\s*(.*)", texto, flags=re.IGNORECASE)
    if minimo:
        return Tolerancia(
            "LIMITE", valor_minimo=para_numero(minimo.group(1)), unidade=minimo.group(2) or None
        )

    maximo = re.fullmatch(rf"{NUMERO}\s*(\S+?)\s*m[aá]x\.?", texto, flags=re.IGNORECASE)
    if maximo:
        return Tolerancia(
            "LIMITE", valor_maximo=para_numero(maximo.group(1)), unidade=maximo.group(2)
        )

    return Tolerancia("CRITERIO")


def nominal_do_texto(descricao: str) -> float | None:
    """Nominal de pontos escritos em graus, ex.: "30° (Q1)" → 30.

    "1º ponto 67 a 80 HR15T" (durômetro) é ordinal, não nominal → None.
    """
    achado = re.match(rf"\s*{NUMERO}\s*[°º](?!\s*ponto)", descricao, flags=re.IGNORECASE)
    return para_numero(achado.group(1)) if achado else None
