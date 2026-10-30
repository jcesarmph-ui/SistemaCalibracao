"""Logo e ícone: dentro do .exe (pedido do usuário em 2026-10-30) ou, fora dele, na pasta de dados.

No .exe, o PyInstaller descompacta os arquivos embutidos em `sys._MEIPASS`; a pasta `dados` ao
lado do .exe fica só com o banco e os backups (e oculta, ver `ocultar_pasta`).
"""

import sys
from pathlib import Path


def recurso(nome: str, pasta_dados: Path) -> Path:
    """Caminho do arquivo `nome` (ex.: logo_mg.png): o embutido no .exe, senão o da pasta."""
    embutidos = getattr(sys, "_MEIPASS", None)
    if embutidos and (Path(embutidos) / "recursos" / nome).is_file():
        return Path(embutidos) / "recursos" / nome
    return pasta_dados / nome


def ocultar_pasta(pasta: Path) -> None:
    """Marca a pasta como oculta no Windows (quem abre a pasta da rede vê só o programa)."""
    if sys.platform != "win32":
        return
    import ctypes

    oculta = 0x2  # FILE_ATTRIBUTE_HIDDEN
    atributos = ctypes.windll.kernel32.GetFileAttributesW(str(pasta))
    if atributos != -1 and not atributos & oculta:
        ctypes.windll.kernel32.SetFileAttributesW(str(pasta), atributos | oculta)
