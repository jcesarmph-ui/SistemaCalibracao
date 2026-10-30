"""Lançador: o "Calibração de Instrumentos.exe" que fica na pasta da rede (pedido de 2026-10-30).

Abrir o programa direto da rede levava 10–15 s (o Windows puxava tudo pela rede a cada vez). O
lançador copia o programa para o próprio PC uma vez por versão e abre a cópia (~1–2 s); o banco
continua só na rede (pasta `dados`), então todos veem os mesmos dados e a trava funciona igual.

Pasta da rede:
    Calibração de Instrumentos.exe   ← o lançador (o que as pessoas abrem)
    _internal\\                       ← do lançador (oculta)
    programa\\                        ← o programa de verdade + versao.txt (oculta)
    dados\\                           ← banco e backups (oculta)

Atualizar = trocar a pasta `programa` (com o programa fechado); cada PC copia a versão nova
sozinho na próxima abertura. Sem conseguir copiar, abre direto da rede (mais devagar).
Não usa PySide6 de propósito: o lançador precisa ser pequeno para abrir rápido.
"""

import os
import shutil
import subprocess
import sys
import threading
import uuid
from pathlib import Path

from calibracao.interface.recursos import ocultar_pasta

NOME_EXE = "Calibração de Instrumentos.exe"
PRONTO = "copia_completa.txt"  # só existe quando a cópia local terminou inteira


def pasta_cache() -> Path:
    base = os.environ.get("LOCALAPPDATA") or str(Path.home())
    return Path(base) / "MG Centro de Servicos" / "Calibracao"


def versao_da_rede(programa: Path) -> str:
    """Versão do programa na rede (ex.: 1.0.0_20261030-153012), gravada ao gerar o .exe."""
    return (programa / "versao.txt").read_text(encoding="utf-8").strip()


def copia_pronta(cache: Path, versao: str) -> bool:
    return (cache / versao / PRONTO).is_file()


def copiar_para_o_pc(programa: Path, cache: Path, versao: str) -> Path:
    """Copia `programa` para cache/versao (se ainda não estiver lá inteiro) e devolve a pasta.

    Copia para uma pasta temporária e só no fim renomeia: uma cópia interrompida (PC desligado no
    meio) nunca é usada, e duas aberturas ao mesmo tempo não se atrapalham.
    """
    destino = cache / versao
    if copia_pronta(cache, versao):
        return destino
    if destino.exists():  # sobra de uma cópia que não terminou
        shutil.rmtree(destino, ignore_errors=True)
    cache.mkdir(parents=True, exist_ok=True)
    temporaria = cache / f"{versao}.copiando-{uuid.uuid4().hex[:8]}"
    shutil.copytree(programa, temporaria)
    (temporaria / PRONTO).write_text(versao, encoding="utf-8")
    try:
        temporaria.rename(destino)
    except OSError:  # outra abertura terminou primeiro: usa a dela
        shutil.rmtree(temporaria, ignore_errors=True)
        if not copia_pronta(cache, versao):
            raise
    return destino


def limpar_versoes_antigas(cache: Path, atual: str) -> None:
    """Apaga do PC as versões que não são a atual (as que estiverem abertas ficam para depois)."""
    if not cache.is_dir():
        return
    for pasta in cache.iterdir():
        if pasta.name != atual:
            shutil.rmtree(pasta, ignore_errors=True)


def _copiar_mostrando_aviso(programa: Path, cache: Path, versao: str) -> Path:
    """Copia numa linha separada, com uma janelinha "Preparando…" (leva ~20–30 s pela rede)."""
    resultado: dict = {}

    def copiar() -> None:
        try:
            resultado["pasta"] = copiar_para_o_pc(programa, cache, versao)
        except Exception as erro:  # noqa: BLE001 — levado de volta para a linha principal
            resultado["erro"] = erro

    linha = threading.Thread(target=copiar, daemon=True)
    linha.start()
    try:
        import tkinter

        janela = tkinter.Tk()
        janela.title("Calibração de Instrumentos")
        janela.configure(bg="#000000")
        janela.resizable(False, False)
        tkinter.Label(janela, text="Preparando o programa neste computador…\n\n"
                      "Só acontece na primeira vez e depois de cada atualização.",
                      bg="#000000", fg="#f0f0f0", font=("Segoe UI", 12), padx=30, pady=25).pack()
        janela.attributes("-topmost", True)

        def conferir() -> None:
            if linha.is_alive():
                janela.after(200, conferir)
            else:
                janela.destroy()

        conferir()
        janela.mainloop()
    except Exception:  # noqa: BLE001 — sem a janelinha, só espera a cópia
        pass
    linha.join()
    if "erro" in resultado:
        raise resultado["erro"]
    return resultado["pasta"]


def main() -> int:
    rede = Path(sys.executable).parent
    programa, dados = rede / "programa", rede / "dados"
    for pasta in (rede / "_internal", programa, dados):
        if pasta.is_dir():
            ocultar_pasta(pasta)
    exe = programa / NOME_EXE
    try:
        versao = versao_da_rede(programa)
        cache = pasta_cache()
        if not copia_pronta(cache, versao):
            _copiar_mostrando_aviso(programa, cache, versao)
        limpar_versoes_antigas(cache, versao)
        exe = cache / versao / NOME_EXE
    except OSError:
        pass  # sem cópia local: abre direto da rede (mais devagar, mas abre)
    ambiente = dict(os.environ, CALIBRACAO_DADOS=str(dados))
    processo = subprocess.Popen([str(exe)], env=ambiente, cwd=str(exe.parent))
    if os.environ.get("CALIBRACAO_FOTO"):  # conferência do pacote: espera o programa fechar
        processo.wait()
    return 0


if __name__ == "__main__":
    sys.exit(main())
