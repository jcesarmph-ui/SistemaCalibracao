"""Lugar oficial do banco: abrir uma CÓPIA (pasta copiada para outro lugar) não pode virar edição.

A trava de edição mora dentro do arquivo do banco, então só coordena quem abre o MESMO arquivo.
Quem abre uma cópia teria a sua própria trava e gravaria num banco que ninguém mais vê. Por isso o
banco guarda o caminho do lugar oficial (o primeiro de onde foi aberto) e o programa compara.

A mesma pasta da rede pode aparecer com caminhos diferentes em cada PC (letra de unidade ou
\\\\servidor\\...): quando o oficial está acessível, pergunta-se ao Windows se é o mesmo arquivo;
só quando não está é que se compara o texto do caminho.
"""

import os
from pathlib import Path


def local_do_banco(banco: Path) -> str:
    """Caminho completo do arquivo do banco, do jeito que fica guardado como oficial."""
    return str(Path(banco).resolve())


def eh_copia(banco: Path, oficial: str) -> bool:
    """True se `banco` não é o arquivo do lugar oficial."""
    caminho_oficial = Path(oficial)
    try:
        if caminho_oficial.is_file():
            return not os.path.samefile(banco, caminho_oficial)
    except OSError:
        pass  # oficial fora do alcance deste PC: compara o texto
    return local_do_banco(banco).casefold() != oficial.casefold()
