"""Monta a ENTREGA (versão sem teste) em dist/entrega/ (pedido de 2026-11-03, versão 1.0.0).

    dist/entrega/
        Calibração de Instrumentos.exe   ← lançador (do pacote de gerar_exe.py)
        _internal\\, programa\\            ← do pacote
        dados\\calibracao.db               ← o banco da entrega, montado da DQ05 (fica como está)

O banco é conferido antes: sem calibrações, sem marca de teste e sem lugar oficial (o 1º lugar
de onde for aberto — a pasta da rede — vira o oficial). Também recebe o mês da implantação
(`metadados.implantado_em`): o seletor de meses do cronograma não mostra nada antes dele.
A pasta inteira é copiada para a rede SEM ser aberta antes.

Uso: .venv/Scripts/python empacotamento/montar_entrega.py   (depois de gerar_exe.py)
"""

import shutil
import sqlite3
import sys
from pathlib import Path

PROJETO = Path(__file__).resolve().parents[1]
NOME = "Calibração de Instrumentos"
PACOTE = PROJETO / "dist" / NOME
ENTREGA = PROJETO / "dist" / "entrega"
BANCO = ENTREGA / "dados" / "calibracao.db"
IMPLANTACAO = "2026-11-01"  # novembro de 2026 (definido pelo usuário)


def conferir_e_marcar(banco: Path) -> str | None:
    """Confere o banco e grava o mês da implantação. Devolve o problema, se houver."""
    conexao = sqlite3.connect(banco)
    try:
        metadados = dict(conexao.execute("SELECT chave, valor FROM metadados"))
        if "banco_de_teste" in metadados:
            return "o banco tem a marca de TESTE"
        if "pasta_oficial" in metadados:
            return "o banco já tem lugar oficial gravado (foi aberto em algum lugar)"
        calibracoes = conexao.execute("SELECT COUNT(*) FROM calibracoes").fetchone()[0]
        if calibracoes:
            return f"o banco tem {calibracoes} calibração(ões): a entrega começa sem nenhuma"
        with conexao:
            conexao.execute("INSERT OR REPLACE INTO metadados (chave, valor) "
                            "VALUES ('implantado_em', ?)", (IMPLANTACAO,))
        return None
    finally:
        conexao.close()


def main() -> int:
    for necessario in (PACOTE / f"{NOME}.exe", PACOTE / "programa", BANCO):
        if not necessario.exists():
            print(f"Falta: {necessario}")
            return 1
    problema = conferir_e_marcar(BANCO)
    if problema:
        print(f"Parei: {problema}. Conferir antes!")
        return 1
    for item in ENTREGA.iterdir():  # troca tudo, menos a pasta dados
        if item.name != "dados":
            shutil.rmtree(item) if item.is_dir() else item.unlink()
    for item in PACOTE.iterdir():
        destino = ENTREGA / item.name
        shutil.copytree(item, destino) if item.is_dir() else shutil.copy2(item, destino)
    versao = (ENTREGA / "programa" / "versao.txt").read_text(encoding="utf-8").strip()
    print(f"Pronto: {ENTREGA}\n  versão {versao}\n  banco conferido (sem calibrações, sem lugar "
          f"oficial); implantação = {IMPLANTACAO[:7]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
