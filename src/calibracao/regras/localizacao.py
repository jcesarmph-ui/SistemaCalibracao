"""Padronização da localização dos instrumentos (pedido do usuário em 2026-10-29).

- Tudo o que é do laboratório vira "Laboratório", "Laboratório - Reserva" ou
  "Laboratório - Orientação indicativa" (a planilha tinha "Lab.", "Reserva Laboratório"…).
- Qualquer menção a orientação indicativa ("Orientativo", "(indicativa)", "(indic.)", "Or. Ind.")
  vira o sufixo " - Orientação indicativa" (na tela, essas palavras têm a cor da etiqueta física).
O resto fica como foi digitado.
"""

import re

ORIENTACAO_INDICATIVA = "Orientação indicativa"

_INDICATIVA = re.compile(
    r"[\s\-–(]*\b(orienta(tiv[oa]|ção\s+indicativa)|indicativ[oa]|indic\.|or\.\s*ind\.?)\)?\s*$",
    re.IGNORECASE,
)
_LABORATORIO = re.compile(r"\blab(\.|oratório|oratorio)?\b", re.IGNORECASE)
_RESERVA = re.compile(r"\breserva\b", re.IGNORECASE)


def padronizar_localizacao(texto: str | None) -> str | None:
    if texto is None or not texto.strip():
        return None
    local = " ".join(texto.split())
    indicativa = bool(_INDICATIVA.search(local))
    if indicativa:
        local = _INDICATIVA.sub("", local).strip(" -–")
    # Mais de um local ("Serralheria / Manutenção", pedido de 2026-11-10): cada um à parte.
    local = " / ".join(_laboratorio(parte.strip()) for parte in local.split("/") if parte.strip())
    if indicativa:
        local = f"{local} - {ORIENTACAO_INDICATIVA}" if local else ORIENTACAO_INDICATIVA
    return local


def _laboratorio(local: str) -> str:
    if _LABORATORIO.search(local):
        return "Laboratório - Reserva" if _RESERVA.search(local) else "Laboratório"
    return local


_SUFIXO = re.compile(r"\s*-\s*(orientação indicativa|reserva)\s*$", re.IGNORECASE)


def local_do_filtro(localizacao: str | None) -> str | None:
    """O local em si, para o filtro: "CT-01 - Orientação indicativa" e "Laboratório - Reserva"
    entram em "CT-01" e "Laboratório" (pedido do usuário em 2026-10-30: ser reserva ou orientação
    indicativa não cria outro local; as etiquetas coloridas da lista mostram qual é qual)."""
    if not localizacao:
        return None
    local = localizacao
    while _SUFIXO.search(local):
        local = _SUFIXO.sub("", local)
    return local or localizacao


RESERVA = "Reserva"
_RESERVA_COM_TRACO = re.compile(r"\s*[-–]?\s*\breserva\b\s*[-–]?\s*", re.IGNORECASE)


def eh_reserva(localizacao: str | None) -> bool:
    """True se a localização diz que o instrumento é reserva (a caixa "Reserva" fica marcada)."""
    return bool(localizacao and _RESERVA.search(localizacao))


def eh_indicativa(localizacao: str | None) -> bool:
    """True se a localização tem a marca de orientação indicativa (caixa da ficha marcada)."""
    return bool(localizacao and _INDICATIVA.search(" ".join(localizacao.split())))


def com_marcas(localizacao: str | None, reserva: bool | None = None,
               indicativa: bool | None = None) -> str | None:
    """Localização com ou sem " - Reserva" / " - Orientação indicativa" (caixas da ficha, pedido
    de 2026-11-03). None = deixa a marca como está.

    Vale para qualquer local ("CT-01 - Reserva"). Com as duas, a reserva vem antes:
    "Laboratório - Reserva - Orientação indicativa". Tirando a marca, a palavra sai inteira.
    """
    local = " ".join((localizacao or "").split())
    tem_indicativa = bool(_INDICATIVA.search(local))
    if tem_indicativa:
        local = _INDICATIVA.sub("", local).strip(" -–")
    tem_reserva = bool(_RESERVA.search(local))
    local = _RESERVA_COM_TRACO.sub(" - ", local).strip(" -–")
    reserva = tem_reserva if reserva is None else reserva
    indicativa = tem_indicativa if indicativa is None else indicativa
    partes = [p for p in (local, RESERVA if reserva else "",
                          ORIENTACAO_INDICATIVA if indicativa else "") if p]
    return " - ".join(partes) or None


def com_reserva(localizacao: str | None, reserva: bool) -> str | None:
    return com_marcas(localizacao, reserva=reserva)
