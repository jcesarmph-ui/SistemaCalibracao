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
    if _LABORATORIO.search(local):
        if _RESERVA.search(local):
            local = "Laboratório - Reserva"
        else:
            local = "Laboratório"
    if indicativa:
        local = f"{local} - {ORIENTACAO_INDICATIVA}" if local else ORIENTACAO_INDICATIVA
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
