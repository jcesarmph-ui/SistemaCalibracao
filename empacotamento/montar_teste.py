"""Monta o programa de TESTE em dist/TESTE - Calibração/ (pedido de 2026-11-03).

O usuário quer um programa onde possa incluir, mudar e excluir à vontade para achar melhorias, sem
bagunçar o banco que vai ser implantado. Por isso:
    - o programa é o MESMO do pacote (dist/Calibração de Instrumentos/): o que se acha no teste
      vale para o oficial;
    - o banco é uma CÓPIA do banco da entrega (dist/entrega/dados/), marcada por dentro como de
      teste (`metadados.banco_de_teste`): o programa mostra "TESTE" no título e uma faixa amarela;
    - o lançador se chama "TESTE - Calibração de Instrumentos.exe", para não confundir na rede.
O banco da entrega só é lido (nunca aberto para escrita) e é conferido: não pode ter a marca de
teste nem lugar oficial gravado.

Uso: .venv/Scripts/python empacotamento/montar_teste.py   (depois de gerar_exe.py)
"""

import hashlib
import shutil
import sqlite3
import sys
from pathlib import Path

PROJETO = Path(__file__).resolve().parents[1]
NOME = "Calibração de Instrumentos"
PACOTE = PROJETO / "dist" / NOME
BANCO_ENTREGA = PROJETO / "dist" / "entrega" / "dados" / "calibracao.db"
TESTE = PROJETO / "dist" / "TESTE - Calibração"
EXE_TESTE = f"TESTE - {NOME}.exe"


def sha256(arquivo: Path) -> str:
    return hashlib.sha256(arquivo.read_bytes()).hexdigest()


def metadados(banco: Path) -> dict[str, str]:
    """Lê os metadados sem gravar nada (modo só leitura)."""
    conexao = sqlite3.connect(f"{banco.resolve().as_uri()}?mode=ro", uri=True)
    try:
        return dict(conexao.execute("SELECT chave, valor FROM metadados"))
    finally:
        conexao.close()


def marcar_como_teste(banco: Path) -> None:
    """Na cópia: marca como de teste e apaga o lugar oficial (o 1º lugar de onde abrir vira o
    oficial, igual à entrega)."""
    conexao = sqlite3.connect(banco)
    try:
        with conexao:
            conexao.execute("DELETE FROM metadados WHERE chave = 'pasta_oficial'")
            conexao.execute("INSERT OR REPLACE INTO metadados (chave, valor) "
                            "VALUES ('banco_de_teste', 'sim')")
    finally:
        conexao.close()


def main() -> int:
    for necessario in (PACOTE / f"{NOME}.exe", PACOTE / "programa", BANCO_ENTREGA):
        if not necessario.exists():
            print(f"Falta: {necessario}")
            return 1
    antes = sha256(BANCO_ENTREGA)
    entrega = metadados(BANCO_ENTREGA)
    if "banco_de_teste" in entrega or "pasta_oficial" in entrega:
        print("O banco da entrega tem marca de teste ou lugar oficial gravado: conferir antes!")
        return 1

    shutil.rmtree(TESTE, ignore_errors=True)
    shutil.copytree(PACOTE, TESTE)
    (TESTE / f"{NOME}.exe").rename(TESTE / EXE_TESTE)
    (TESTE / "dados").mkdir()
    shutil.copy2(BANCO_ENTREGA, TESTE / "dados" / "calibracao.db")
    marcar_como_teste(TESTE / "dados" / "calibracao.db")

    if sha256(BANCO_ENTREGA) != antes:  # garantia: a entrega ficou igual
        print("ATENÇÃO: o banco da entrega mudou!")
        return 1
    print(f"Pronto: {TESTE}\n  abrir por: {EXE_TESTE}\n  banco de teste marcado; entrega intacta.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
