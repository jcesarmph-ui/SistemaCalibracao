"""Ícones do programa (Material Symbols do Google, licença Apache 2.0 — ver `icones/LEIAME.md`).

Os SVG ficam pretos, como foram baixados; aqui ganham a cor do tema. `icone()` dá o QIcon para
botões; `arquivo_do_icone()` grava uma cópia colorida na pasta temporária, para o estilo do Qt
(que só aceita imagem por arquivo, ex.: a setinha do campo de data).
"""

import re
import tempfile
from pathlib import Path

PASTA = Path(__file__).parent / "icones"


def svg_colorido(nome: str, cor: str) -> str:
    """O SVG `nome` (sem .svg) com tudo pintado de `cor` (ex.: "#f0f0f0")."""
    texto = (PASTA / f"{nome}.svg").read_text(encoding="utf-8")
    return re.sub(r"<path ", f'<path fill="{cor}" ', texto)


def icone(nome: str, cor: str, tamanho: int = 48):
    """QIcon do ícone na cor pedida (desenhado em `tamanho` px, nítido com zoom de tela)."""
    from PySide6.QtCore import QByteArray, Qt
    from PySide6.QtGui import QIcon, QPainter, QPixmap
    from PySide6.QtSvg import QSvgRenderer

    renderizador = QSvgRenderer(QByteArray(svg_colorido(nome, cor).encode("utf-8")))
    imagem = QPixmap(tamanho, tamanho)
    imagem.fill(Qt.transparent)
    pintor = QPainter(imagem)
    pintor.setRenderHint(QPainter.Antialiasing)
    renderizador.render(pintor)
    pintor.end()
    return QIcon(imagem)


def arquivo_do_icone(nome: str, cor: str) -> str:
    """Grava o SVG colorido na pasta temporária (se mudou) e devolve o caminho com "/" (como o
    estilo do Qt espera). Sem conseguir gravar, devolve "" (fica sem o ícone)."""
    arquivo = Path(tempfile.gettempdir()) / f"calibracao_{nome}_{cor.lstrip('#')}.svg"
    conteudo = svg_colorido(nome, cor)
    try:
        if not arquivo.is_file() or arquivo.read_text(encoding="utf-8") != conteudo:
            arquivo.write_text(conteudo, encoding="utf-8")
    except OSError:
        return ""
    return arquivo.as_posix()
