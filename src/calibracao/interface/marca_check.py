"""Imagem do ✓ das caixinhas marcadas (pedido do usuário em 2026-11-03).

Caixinha desmarcada = contorno branco vazio; marcada = o mesmo contorno com um ✓ branco dentro.
O estilo do Qt só desenha o ✓ a partir de um arquivo de imagem, então o programa gera um PNG
pequeno (sem depender do Qt nem de arquivo de fora) e o grava na pasta temporária do Windows.
"""

import math
import struct
import tempfile
import zlib
from pathlib import Path

TAMANHO = 36  # px (o estilo mostra em 18 px: fica nítido em tela com zoom)
# O ✓: duas retas, em coordenadas da imagem.
TRACOS = [((8.0, 19.0), (15.0, 26.0)), ((15.0, 26.0), (28.0, 10.0))]
ESPESSURA = 2.6  # metade da largura do traço, em px


def _distancia(ponto, inicio, fim) -> float:
    (px, py), (ax, ay), (bx, by) = ponto, inicio, fim
    dx, dy = bx - ax, by - ay
    t = max(0.0, min(1.0, ((px - ax) * dx + (py - ay) * dy) / (dx * dx + dy * dy)))
    return math.hypot(px - (ax + t * dx), py - (ay + t * dy))


def png_do_check(cor: str = "#ffffff") -> bytes:
    """PNG RGBA: ✓ na `cor` (com borda suavizada) sobre fundo transparente."""
    vermelho, verde, azul = (int(cor[i:i + 2], 16) for i in (1, 3, 5))
    linhas = []
    for y in range(TAMANHO):
        linha = bytearray([0])  # filtro "nenhum" da linha
        for x in range(TAMANHO):
            d = min(_distancia((x + 0.5, y + 0.5), a, b) for a, b in TRACOS)
            alfa = max(0.0, min(1.0, ESPESSURA + 0.5 - d))
            linha += bytes([vermelho, verde, azul, round(alfa * 255)])
        linhas.append(bytes(linha))

    def bloco(tipo: bytes, dados: bytes) -> bytes:
        return (struct.pack(">I", len(dados)) + tipo + dados
                + struct.pack(">I", zlib.crc32(tipo + dados) & 0xFFFFFFFF))

    cabecalho = struct.pack(">IIBBBBB", TAMANHO, TAMANHO, 8, 6, 0, 0, 0)
    return (b"\x89PNG\r\n\x1a\n" + bloco(b"IHDR", cabecalho)
            + bloco(b"IDAT", zlib.compress(b"".join(linhas), 9)) + bloco(b"IEND", b""))


def caminho_do_check(cor: str = "#ffffff") -> str:
    """Grava o PNG na pasta temporária (se ainda não estiver lá) e devolve o caminho com "/"
    (como o estilo do Qt espera). Sem conseguir gravar, devolve "" (fica sem o ✓)."""
    arquivo = Path(tempfile.gettempdir()) / f"calibracao_check_{cor.lstrip('#')}.png"
    conteudo = png_do_check(cor)
    try:
        if not arquivo.is_file() or arquivo.read_bytes() != conteudo:
            arquivo.write_bytes(conteudo)
    except OSError:
        return ""
    return arquivo.as_posix()
