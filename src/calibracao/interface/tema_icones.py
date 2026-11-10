"""Ícones do programa (Material Symbols do Google, licença Apache 2.0 — ver `icones/LEIAME.md`).

Os SVG ficam pretos, como foram baixados; aqui ganham a cor do tema. `icone()` dá o QIcon para
botões e abas; `arquivo_do_icone()` grava uma cópia colorida na pasta temporária, para o estilo
do Qt e para textos com <img> (que só aceitam imagem por arquivo).
"""

import html
import re
import tempfile
from pathlib import Path

PASTA = Path(__file__).parent / "icones"
TAMANHO_BOTAO = 22  # px do ícone nos botões e abas


def svg_colorido(nome: str, cor: str) -> str:
    """O SVG `nome` (sem .svg) com tudo pintado de `cor` (ex.: "#f0f0f0")."""
    texto = (PASTA / f"{nome}.svg").read_text(encoding="utf-8")
    return re.sub(r"<path ", f'<path fill="{cor}" ', texto)


def pixmap(nome: str, cor: str, tamanho: int = 48):
    """Imagem do ícone na cor pedida (desenhada em `tamanho` px)."""
    from PySide6.QtCore import QByteArray, Qt
    from PySide6.QtGui import QPainter, QPixmap
    from PySide6.QtSvg import QSvgRenderer

    renderizador = QSvgRenderer(QByteArray(svg_colorido(nome, cor).encode("utf-8")))
    imagem = QPixmap(tamanho, tamanho)
    imagem.fill(Qt.transparent)
    pintor = QPainter(imagem)
    pintor.setRenderHint(QPainter.Antialiasing)
    renderizador.render(pintor)
    pintor.end()
    return imagem


def icone(nome: str, cor: str, tamanho: int = 48):
    """QIcon do ícone na cor pedida (desenhado grande, fica nítido com zoom de tela)."""
    from PySide6.QtGui import QIcon

    return QIcon(pixmap(nome, cor, tamanho))


def por_icone(botao, nome: str, cor: str) -> None:
    """Ícone na frente do texto do botão (o texto continua: ninguém precisa adivinhar)."""
    from PySide6.QtCore import QSize

    botao.setIcon(icone(nome, cor))
    botao.setIconSize(QSize(TAMANHO_BOTAO, TAMANHO_BOTAO))


def lupa(campo, cor: str) -> None:
    """Lupa no começo do campo de pesquisa."""
    from PySide6.QtWidgets import QLineEdit

    campo.addAction(icone("search", cor), QLineEdit.LeadingPosition)


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


def html_com_icones(texto: str, simbolos: dict[str, tuple[str, str]],
                    tamanho: int = 20) -> str | None:
    """Texto de aviso com ✔ ✖ ⚠ trocados pelo ícone (em HTML); None se não tem símbolo.

    `simbolos` = símbolo → (nome do ícone, cor), ex.: {"✔": ("check_circle", "#43a047")}.
    """
    if not any(s in texto for s in simbolos):
        return None
    partes = []
    for linha in texto.split("\n"):
        linha = html.escape(linha)
        for simbolo, (nome, cor) in simbolos.items():
            caminho = arquivo_do_icone(nome, cor)
            if caminho:
                img = (f'<img src="{caminho}" width="{tamanho}" height="{tamanho}" '
                       'style="vertical-align: middle;">')
                linha = re.sub(re.escape(simbolo) + r"\s?", img + "&nbsp;", linha)
        partes.append(linha)
    return "<br>".join(partes)
