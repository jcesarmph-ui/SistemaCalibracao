"""Um nome só para o mesmo tipo ou local (pedido do usuário em 2026-11-10).

- Tipos ou locais que só mudam nas maiúsculas ("Lâmina de Folga" × "Lâmina de folga") são o mesmo:
  ficam com a grafia que a maioria dos instrumentos usa.
- "Régua graduada para furos" passa a ser "Régua graduada" (decisão do usuário).
- A localização pode ter mais de um local, separados por " / " ("Serralheria / Manutenção"): o
  instrumento aparece no filtro de cada um, e não num local novo "Serralheria / Manutenção".
"""

import collections
import re
import unicodedata
from collections.abc import Iterable

from calibracao.regras.localizacao import local_do_filtro

# Tipos que o usuário mandou juntar num só (chave já sem maiúsculas → nome que fica).
TIPOS_JUNTADOS = {"régua graduada para furos": "Régua graduada"}

SEPARADOR = " / "
_SUFIXOS = re.compile(r"(\s*-\s*(orientação indicativa|reserva)\s*)+$", re.IGNORECASE)


def chave(texto: str) -> str:
    """O que decide se dois nomes são o mesmo: sem espaços repetidos e sem maiúsculas."""
    return " ".join(texto.split()).casefold()


def ordem(texto: str) -> str:
    """Para pôr em ordem alfabética sem os acentos atrapalharem ("Máquina" antes de "Medidor")."""
    sem_acento = unicodedata.normalize("NFD", chave(texto))
    return "".join(c for c in sem_acento if not unicodedata.combining(c))


def _limpo(texto: str) -> str:
    return " ".join(texto.split())


def grafias_preferidas(nomes: Iterable[str]) -> dict[str, str]:
    """chave → grafia mais usada. Empate: a que começa com maiúscula e, entre essas, a com menos
    maiúsculas ("Manutenção" e não "manutenção"; "Lâmina de folga" e não "Lâmina de Folga")."""
    por_chave: dict[str, collections.Counter] = collections.defaultdict(collections.Counter)
    for nome in nomes:
        if nome and nome.strip():
            por_chave[chave(nome)][_limpo(nome)] += 1
    return {k: min(contagem, key=lambda g: (-contagem[g], not g[:1].isupper(),
                                            sum(c.isupper() for c in g), g))
            for k, contagem in por_chave.items()}


# --- Tipos ---------------------------------------------------------------------------------


def tipo_padrao(tipo: str | None, preferidas: dict[str, str]) -> str | None:
    """O tipo com o nome que vale (junta os da lista do usuário e a grafia da maioria)."""
    if tipo is None or not tipo.strip():
        return tipo
    k = chave(tipo)
    if k in TIPOS_JUNTADOS:
        k = chave(TIPOS_JUNTADOS[k])
        return preferidas.get(k, TIPOS_JUNTADOS[chave(tipo)])
    return preferidas.get(k, _limpo(tipo))


def preferidas_dos_tipos(tipos: Iterable[str]) -> dict[str, str]:
    tipos = list(tipos)
    juntados = [TIPOS_JUNTADOS.get(chave(t), t) for t in tipos if t]
    return grafias_preferidas(juntados)


# --- Localização ---------------------------------------------------------------------------


def locais(localizacao: str | None) -> list[str]:
    """Os locais de uma localização, sem as marcas de reserva/orientação indicativa:
    "Serralheria / Manutenção - Orientação indicativa" → ["Serralheria", "Manutenção"]."""
    local = local_do_filtro(localizacao)
    if not local:
        return []
    return [_limpo(parte) for parte in local.split("/") if parte.strip()]


def preferidas_dos_locais(localizacoes: Iterable[str | None]) -> dict[str, str]:
    return grafias_preferidas(parte for loc in localizacoes for parte in locais(loc))


def localizacao_padrao(localizacao: str | None, preferidas: dict[str, str]) -> str | None:
    """Cada local com a grafia que vale, separados por " / ", e as marcas no fim como estavam.
    Local repetido sai ("CT-01 / ct-01" → "CT-01")."""
    if localizacao is None or not localizacao.strip():
        return localizacao
    texto = _limpo(localizacao)
    sufixo = _SUFIXOS.search(texto)
    marcas = sufixo.group(0) if sufixo and sufixo.start() > 0 else ""
    corpo = texto[: len(texto) - len(marcas)] if marcas else texto
    partes, vistas = [], set()
    for parte in corpo.split("/"):
        if not parte.strip():
            continue
        k = chave(parte)
        if k not in vistas:
            vistas.add(k)
            partes.append(preferidas.get(k, _limpo(parte)))
    if not partes:
        return texto
    return SEPARADOR.join(partes) + marcas
