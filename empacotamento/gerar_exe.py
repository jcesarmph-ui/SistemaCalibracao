"""Gera o pacote do programa (PyInstaller) em dist/Calibração de Instrumentos/.

O que vai para a pasta da rede (ver calibracao/lancador.py):
    Calibração de Instrumentos.exe   ← lançador: copia o programa para o PC e o abre (~1–2 s)
    _internal\\                       ← do lançador
    programa\\                        ← o programa (PySide6) + versao.txt
A pasta dados\\ (banco e backups) é colocada ao lado na entrega; o lançador oculta as pastas, então
na rede só se vê o .exe. Logo e ícone vão dentro do programa (interface/recursos.py).
Atualizar = trocar a pasta "programa" (com o programa fechado); cada PC copia a versão nova sozinho.
Nada disso vai para o GitHub (dist/ está no .gitignore).

Uso: .venv/Scripts/python empacotamento/gerar_exe.py
"""

import datetime
import shutil
import sys
from pathlib import Path

import PyInstaller.__main__

PROJETO = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJETO / "src"))
from calibracao import __version__  # noqa: E402

NOME = "Calibração de Instrumentos"
ICONE = PROJETO / "dados" / "icone_mg.ico"  # símbolo da MG (fora do Git, como o logo)
TRABALHO = PROJETO / "dist" / "_gerando"
PACOTE = PROJETO / "dist" / NOME

# Módulos que o programa não usa (entravam junto e só deixavam a cópia mais pesada).
SEM_USO = ["calibracao.importacao", "openpyxl", "pytest", "pandas", "tkinter",
           "PySide6.QtQuick", "PySide6.QtQml", "PySide6.QtPdf", "PySide6.QtNetwork"]
# Arquivos do Qt sem uso numa tela comum: OpenGL por software e traduções.
SOBRAS_QT = ["opengl32sw.dll", "translations"]


def gerar(script: Path, saida: Path, excluir: list[str], dados: list[str]) -> Path:
    argumentos = [str(script), "--name", NOME, "--onedir", "--windowed", "--icon", str(ICONE),
                  "--paths", str(PROJETO / "src"), "--distpath", str(saida),
                  "--workpath", str(TRABALHO / "build"), "--specpath", str(TRABALHO / "build"),
                  "--noconfirm", "--clean"]
    for modulo in excluir:
        argumentos += ["--exclude-module", modulo]
    for arquivo in dados:
        argumentos += ["--add-data", f"{PROJETO / 'dados' / arquivo};recursos"]
    PyInstaller.__main__.run(argumentos)
    return saida / NOME


def main() -> int:
    if not ICONE.is_file():
        print(f"Falta o ícone: {ICONE}")
        return 1
    shutil.rmtree(TRABALHO, ignore_errors=True)
    programa = gerar(PROJETO / "src" / "calibracao" / "__main__.py", TRABALHO / "programa",
                     SEM_USO, ["logo_mg.png", "icone_mg.png"])
    for sobra in SOBRAS_QT:
        caminho = programa / "_internal" / "PySide6" / sobra
        if caminho.is_dir():
            shutil.rmtree(caminho)
        elif caminho.is_file():
            caminho.unlink()
    versao = f"{__version__}_{datetime.datetime.now():%Y%m%d-%H%M%S}"
    (programa / "versao.txt").write_text(versao, encoding="utf-8")

    # O lançador não usa PySide6 nem Matplotlib: fica pequeno para abrir rápido da rede.
    lancador = gerar(PROJETO / "src" / "calibracao" / "lancador.py", TRABALHO / "lancador",
                     ["PySide6", "matplotlib", "numpy", "PIL", "pandas", "openpyxl", "pytest"], [])

    shutil.rmtree(PACOTE, ignore_errors=True)
    shutil.copytree(lancador, PACOTE)
    shutil.copytree(programa, PACOTE / "programa")
    shutil.rmtree(TRABALHO, ignore_errors=True)

    def tamanho(pasta: Path) -> float:
        return sum(f.stat().st_size for f in pasta.rglob("*") if f.is_file()) / 1_048_576

    print(f"\nGerado: {PACOTE}\n  versão {versao}\n  lançador: "
          f"{tamanho(PACOTE) - tamanho(PACOTE / 'programa'):.0f} MB | programa: "
          f"{tamanho(PACOTE / 'programa'):.0f} MB")
    return 0


if __name__ == "__main__":
    sys.exit(main())
