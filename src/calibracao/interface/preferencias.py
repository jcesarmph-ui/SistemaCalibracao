"""Preferências de cada pessoa (usuário do Windows), não do banco: ficam no registro do Windows
de quem usa (HKEY_CURRENT_USER), então cada um vê o programa do seu jeito, em qualquer PC.
"""

from PySide6.QtCore import QSettings

EMPRESA, PROGRAMA = "MG Centro de Servicos", "Calibracao"


def _configuracoes() -> QSettings:
    return QSettings(EMPRESA, PROGRAMA)


def ler_tema() -> str:
    """"escuro" (padrão de todos os programas da MG) ou "claro"."""
    valor = _configuracoes().value("tema", "escuro")
    return valor if valor in ("escuro", "claro") else "escuro"


def gravar_tema(tema: str) -> None:
    _configuracoes().setValue("tema", tema)
