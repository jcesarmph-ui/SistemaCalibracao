"""Arquivos PDF dos certificados de calibração (pedido do usuário em 2026-11-10).

Os PDFs ficam na pasta `certificados/` ao lado do banco (na rede, dentro da pasta oculta `dados`);
o banco guarda só a ligação (tabela `certificados`). Assim o banco continua leve e rápido na rede.

- O arquivo escolhido é **copiado** (o original da pessoa fica onde estava) com um nome próprio,
  que nunca se repete: um PDF guardado nunca é sobrescrito.
- A cópia é conferida pelo SHA-256 (a "impressão digital" do arquivo): se não bater, não vale.
- O backup diário copia para `backup/certificados/` os PDFs que ainda não estão lá.
"""

import datetime
import hashlib
import re
import shutil
import unicodedata
from pathlib import Path

PASTA = "certificados"
TAMANHO_MAXIMO = 50 * 1024 * 1024  # 50 MB: certificado escaneado costuma ter de 0,2 a 5 MB


class ErroDoArquivo(Exception):
    """O arquivo escolhido não serve (não é PDF, grande demais, cópia falhou...)."""


def sha256(arquivo: Path) -> str:
    resumo = hashlib.sha256()
    with open(arquivo, "rb") as aberto:
        for bloco in iter(lambda: aberto.read(1024 * 1024), b""):
            resumo.update(bloco)
    return resumo.hexdigest()


def _limpo(texto: str) -> str:
    """Só letras sem acento, números e hífen (nome de arquivo seguro em qualquer PC)."""
    sem_acento = unicodedata.normalize("NFD", texto)
    sem_acento = "".join(c for c in sem_acento if not unicodedata.combining(c))
    return re.sub(r"[^A-Za-z0-9-]+", "-", sem_acento).strip("-")[:40] or "sem-numero"


def nome_do_arquivo(codigo: str, numero: str | None, data: datetime.date,
                    agora: datetime.datetime) -> str:
    """Ex.: PAQ-018_2026-11-10_CERT-1234_20261110-153012.pdf (o fim garante que não repete)."""
    return (f"{_limpo(codigo)}_{data.isoformat()}_{_limpo(numero or '')}_"
            f"{agora.strftime('%Y%m%d-%H%M%S-%f')}.pdf")


def conferir_pdf(arquivo: Path) -> None:
    """Recusa o que não é um PDF de verdade (ErroDoArquivo com o motivo, para a tela)."""
    if not arquivo.is_file():
        raise ErroDoArquivo(f"O arquivo não foi encontrado: {arquivo}")
    if arquivo.suffix.lower() != ".pdf":
        raise ErroDoArquivo("Escolha um arquivo PDF (.pdf).")
    tamanho = arquivo.stat().st_size
    if tamanho == 0:
        raise ErroDoArquivo("O arquivo está vazio.")
    if tamanho > TAMANHO_MAXIMO:
        raise ErroDoArquivo(f"O PDF tem {tamanho / 1024 / 1024:.0f} MB; o máximo é "
                            f"{TAMANHO_MAXIMO // 1024 // 1024} MB.")
    with open(arquivo, "rb") as aberto:
        if not aberto.read(1024).lstrip().startswith(b"%PDF"):
            raise ErroDoArquivo("O arquivo não é um PDF válido (está corrompido ou só foi "
                                "renomeado para .pdf).")


def guardar(origem: Path, pasta_dados: Path, nome: str,
            subpasta: str = PASTA) -> tuple[Path, str, int]:
    """Copia o PDF para a pasta dos certificados (ou outra `subpasta`, ex.: relatorios) e
    confere. Devolve (destino, sha256, tamanho).

    Copia primeiro com nome provisório e só renomeia no fim: uma cópia interrompida (rede caiu)
    nunca aparece como certificado."""
    conferir_pdf(origem)
    pasta = pasta_dados / subpasta
    pasta.mkdir(exist_ok=True)
    destino = pasta / nome
    provisorio = destino.with_suffix(".copiando")
    esperado = sha256(origem)
    try:
        shutil.copyfile(origem, provisorio)
        if sha256(provisorio) != esperado:
            raise ErroDoArquivo("A cópia do PDF para a pasta da rede saiu diferente do original. "
                                "Tente de novo.")
        provisorio.replace(destino)
    except OSError as erro:
        raise ErroDoArquivo(f"Não foi possível copiar o PDF para a pasta da rede: {erro}") from erro
    finally:
        provisorio.unlink(missing_ok=True)
    return destino, esperado, destino.stat().st_size


def apagar(pasta_dados: Path, nome: str) -> None:
    """Apaga o PDF de vez (só quando ele é excluído permanentemente da Lixeira)."""
    (pasta_dados / PASTA / nome).unlink(missing_ok=True)


def espelhar_no_backup(pasta_dados: Path, subpasta: str = PASTA) -> int:
    """Copia para `backup/<subpasta>/` os PDFs que ainda não estão lá (os guardados nunca
    mudam, então basta copiar os novos). Devolve quantos copiou."""
    origem = pasta_dados / subpasta
    if not origem.is_dir():
        return 0
    destino = pasta_dados / "backup" / subpasta
    destino.mkdir(parents=True, exist_ok=True)
    copiados = 0
    for pdf in origem.glob("*.pdf"):
        alvo = destino / pdf.name
        if not alvo.exists():
            provisorio = alvo.with_suffix(".copiando")
            shutil.copyfile(pdf, provisorio)
            provisorio.replace(alvo)
            copiados += 1
    return copiados
