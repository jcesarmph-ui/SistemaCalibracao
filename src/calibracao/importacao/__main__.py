"""Monta o banco novo a partir da planilha DQ05.

Uso:
    .venv/Scripts/python -m calibracao.importacao "caminho/da/DQ05.xlsx"
        [--banco dados/calibracao.db] [--conferencia dados/conferencia_importacao.xlsx]

A planilha original nunca é aberta diretamente: o programa lê uma cópia temporária e confere,
pela impressão digital (SHA-256), que o original continua idêntico no fim.
"""

import argparse
import hashlib
import shutil
import sys
import tempfile
from collections import Counter
from pathlib import Path

from calibracao.importacao.conferencia import gerar_conferencia
from calibracao.importacao.gravacao import gravar_banco
from calibracao.importacao.leitura import ler_planilha


def sha256(caminho: Path) -> str:
    resumo = hashlib.sha256()
    with caminho.open("rb") as arquivo:
        for bloco in iter(lambda: arquivo.read(1 << 20), b""):
            resumo.update(bloco)
    return resumo.hexdigest()


def main(argumentos: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Monta o banco do CALIB a partir da DQ05.")
    parser.add_argument("planilha", type=Path)
    parser.add_argument("--banco", type=Path, default=Path("dados/calibracao.db"))
    parser.add_argument(
        "--conferencia", type=Path, default=Path("dados/conferencia_importacao.xlsx")
    )
    opcoes = parser.parse_args(argumentos)

    if opcoes.banco.exists():
        print(f"ERRO: {opcoes.banco} já existe. Apague ou renomeie antes de importar de novo.")
        return 1

    impressao_antes = sha256(opcoes.planilha)
    with tempfile.TemporaryDirectory() as pasta:
        copia = Path(pasta) / "dq05.xlsx"
        shutil.copyfile(opcoes.planilha, copia)
        resultado = ler_planilha(copia)
    impressao_depois = sha256(opcoes.planilha)

    gravar_banco(resultado, opcoes.banco, opcoes.planilha.name, impressao_antes)
    gerar_conferencia(resultado, opcoes.conferencia)

    instrumentos = resultado.instrumentos
    com_plano = [i for i in instrumentos if i.pontos]
    tipos = Counter(p.tipo for i in instrumentos for p in i.pontos)
    print(f"Instrumentos importados: {len(instrumentos)} "
          f"({len(com_plano)} com plano, {len(instrumentos) - len(com_plano)} sem plano)")
    print(f"Pontos: {sum(tipos.values())} — " + ", ".join(f"{t}: {n}" for t, n in tipos.items()))
    print(f"Fora do programa (desativados): {len(resultado.excluidos)}")
    print(f"Avisos: {len(resultado.avisos)}")
    print(f"Banco: {opcoes.banco}")
    print(f"Conferência: {opcoes.conferencia}")
    if impressao_antes == impressao_depois:
        print("Planilha original intacta (impressão digital igual antes e depois).")
        return 0
    print("ATENÇÃO: a planilha original mudou durante a importação (alguém salvou?).")
    return 2


if __name__ == "__main__":
    sys.exit(main())
