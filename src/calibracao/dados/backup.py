"""Backup diário automático do banco, na pasta `backup/` ao lado dele (padrão do usuário).

Uma cópia por dia, feita na primeira abertura do programa naquele dia; guarda as 30 mais recentes
(decisão do usuário em 2026-10-29). A cópia usa a API de backup do SQLite, que gera um arquivo
consistente mesmo se outra pessoa estiver com o programa aberto.
"""

import datetime
import sqlite3
from pathlib import Path

COPIAS_MANTIDAS = 30


def fazer_backup_diario(banco: Path, hoje: datetime.date,
                        manter: int = COPIAS_MANTIDAS) -> Path | None:
    """Faz a cópia do dia (se ainda não existir) e apaga as mais antigas. Devolve a cópia nova."""
    pasta = banco.parent / "backup"
    pasta.mkdir(exist_ok=True)
    destino = pasta / f"{banco.stem}_{hoje.isoformat()}{banco.suffix}"
    nova = None
    if not destino.exists():
        provisorio = destino.with_suffix(".tmp")
        origem = sqlite3.connect(banco, timeout=10)
        copia = sqlite3.connect(provisorio)
        try:
            origem.backup(copia)
        finally:
            copia.close()
            origem.close()
        provisorio.replace(destino)  # só aparece com o nome final se a cópia terminou
        nova = destino
    copias = sorted(pasta.glob(f"{banco.stem}_????-??-??{banco.suffix}"))
    for antiga in copias[:-manter]:
        antiga.unlink()
    return nova
