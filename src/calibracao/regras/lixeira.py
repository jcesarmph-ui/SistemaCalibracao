"""Lixeira (exclusão lógica).

Lixeira = registrado por engano. Regras do protótipo: restaurar exige o "pai" ativo (ponto → plano,
instrumento → plano, calibração → instrumento); excluir permanentemente exige digitar EXCLUIR e
não é permitido com dependências — exceto a calibração, que pode ser apagada de vez junto com os
seus pontos medidos (decisão do usuário em 2026-10-29: pode ter sido registrada por engano).

Desativar não é Lixeira: ver `calibracao.regras.condicao`.
"""

from enum import StrEnum

CONFIRMACAO_EXCLUSAO = "EXCLUIR"


class Tipo(StrEnum):
    INSTRUMENTO = "Instrumento"
    PLANO = "Plano"
    PONTO = "Ponto do plano"
    CALIBRACAO = "Calibração"


PAI = {Tipo.PONTO: Tipo.PLANO, Tipo.INSTRUMENTO: Tipo.PLANO, Tipo.CALIBRACAO: Tipo.INSTRUMENTO}


def bloqueio_restaurar(tipo: Tipo, pai_na_lixeira: bool) -> str | None:
    """Motivo que impede restaurar, ou None se pode."""
    if pai_na_lixeira:
        pai = PAI[tipo].lower()
        return f"Restaure primeiro o {pai} ao qual este item pertence."
    return None


def bloqueio_exclusao_permanente(tipo: Tipo, confirmacao: str,
                                 tem_dependencias: bool) -> str | None:
    """Motivo que impede apagar de vez, ou None se pode.

    `tem_dependencias`: há outros registros ligados a este (ex.: plano usado por instrumentos ou
    com pontos; instrumento com calibrações). Os pontos medidos de uma calibração não contam: são
    apagados com ela.
    """
    if confirmacao.strip() != CONFIRMACAO_EXCLUSAO:
        return f"Para excluir permanentemente, digite {CONFIRMACAO_EXCLUSAO}."
    if tem_dependencias and tipo != Tipo.CALIBRACAO:
        return "Não é possível excluir permanentemente: há registros ligados a este item."
    return None
