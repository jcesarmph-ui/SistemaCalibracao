"""Gera o "Calibração de Instrumentos.exe" (PyInstaller) em dist/.

Um arquivo só, para atualizar seja só trocar o .exe (com o programa fechado por todos). Logo e
ícone vão dentro dele (interface/recursos.py); o banco e os backups ficam na pasta
dados/ ao lado do .exe, que o programa marca como oculta.
O .exe NUNCA vai para o GitHub (dist/ está no .gitignore).

Uso: .venv/Scripts/python empacotamento/gerar_exe.py
"""

import shutil
import sys
from pathlib import Path

import PyInstaller.__main__

PROJETO = Path(__file__).resolve().parents[1]
NOME = "Calibração de Instrumentos"
ICONE = PROJETO / "dados" / "icone_mg.ico"  # símbolo da MG (fora do Git, como o logo)


def main() -> int:
    if not ICONE.is_file():
        print(f"Falta o ícone: {ICONE}")
        return 1
    PyInstaller.__main__.run([
        str(PROJETO / "src" / "calibracao" / "__main__.py"),
        "--name", NOME,
        "--onefile",            # um .exe só
        "--windowed",           # sem a janela preta do console
        "--icon", str(ICONE),
        "--add-data", f"{PROJETO / 'dados' / 'logo_mg.png'};recursos",
        "--add-data", f"{PROJETO / 'dados' / 'icone_mg.png'};recursos",
        "--paths", str(PROJETO / "src"),
        # Só o que o programa usa: o importador da planilha e as ferramentas de teste ficam fora.
        "--exclude-module", "calibracao.importacao",
        "--exclude-module", "openpyxl",
        "--exclude-module", "pytest",
        "--exclude-module", "tkinter",
        "--distpath", str(PROJETO / "dist"),
        "--workpath", str(PROJETO / "build"),
        "--specpath", str(PROJETO / "build"),
        "--noconfirm",
        "--clean",
    ])
    exe = PROJETO / "dist" / f"{NOME}.exe"
    print(f"\nGerado: {exe} ({exe.stat().st_size / 1_048_576:.0f} MB)")
    shutil.rmtree(PROJETO / "build", ignore_errors=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
