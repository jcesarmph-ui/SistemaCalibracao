"""Desenha o relatório (do mês ou do ano) em PDF, folha A4 em pé: números, os gráficos do
painel da aba Indicadores, as calibrações do período e as ALTERAÇÕES (pedido de 2026-11-10;
layout aprovado por foto). Se não couber numa folha, continua na seguinte (o cabeçalho da
tabela se repete).
"""

import datetime
from pathlib import Path

from PySide6.QtCore import QMarginsF, QPointF, QRectF, Qt
from PySide6.QtGui import QColor, QFont, QImage, QPageLayout, QPageSize, QPainter, QPdfWriter, QPen

from calibracao.regras import indicadores as ind
from calibracao.regras.relatorio import MENSAL, ConteudoRelatorio

DPI = 300
MM = DPI / 25.4
MARGEM = 12.0
LARGURA = 210 - 2 * MARGEM
FIM_DA_PAGINA = 297 - 14.0      # o rodapé fica embaixo disto
CORES_NUMERO = {"": "#111111", "certo": "#2e7d32", "aviso": "#8d6e00", "erro": "#c62828"}
FAIXAS = {"Aprovado": ("#1b5e20", "#ffffff"), "Reprovado - Desativado": ("#b71c1c", "#ffffff"),
          "Reprovado": ("#b71c1c", "#ffffff"), "Vencida": ("#b71c1c", "#ffffff"),
          "Pendente": ("#ffd54f", "#000000"), "Orientação indicativa": ("#ffd54f", "#c62828")}
SIMBOLO = {"erro": ("✖", "#c62828"), "aviso": ("⚠", "#8d6e00"), "info": ("•", "#111111")}
COLUNAS = [("Código", 16), ("Tipo", 30), ("Localização", 24), ("Feita em", 17),
           ("Nº certificado", 21), ("Laboratório", 27), ("Parecer final / situação", 31),
           ("Custo", 20)]
ALTURA_LINHA = 5.5
ALTURA_GRAFICO = 50.0


class _Folha:
    """Pintor do PDF em milímetros, com troca de página e rodapé."""

    def __init__(self, destino: Path, rodape: str) -> None:
        self.escritor = QPdfWriter(str(destino))
        self.escritor.setPageLayout(QPageLayout(QPageSize(QPageSize.A4), QPageLayout.Portrait,
                                                QMarginsF(0, 0, 0, 0), QPageLayout.Millimeter))
        self.escritor.setResolution(DPI)
        self.escritor.setTitle("DQ-05 Calibração de Instrumentos — relatório")
        self.p = QPainter(self.escritor)
        self.p.setRenderHint(QPainter.Antialiasing)
        self.p.setRenderHint(QPainter.SmoothPixmapTransform)
        self.rodape = rodape
        self.pagina = 1
        self.y = MARGEM

    @staticmethod
    def r(x, y, w, h) -> QRectF:
        return QRectF(x * MM, y * MM, w * MM, h * MM)

    @staticmethod
    def fonte(pt: float, negrito=False, italico=False) -> QFont:
        fonte = QFont("Segoe UI")
        fonte.setPixelSize(max(1, int(pt * 0.3528 * MM)))
        fonte.setBold(negrito)
        fonte.setItalic(italico)
        return fonte

    def texto(self, x, y, w, h, conteudo, pt=8.0, negrito=False, cor="#111111",
              alinhar=Qt.AlignLeft, italico=False) -> None:
        self.p.setPen(QColor(cor))
        self.p.setFont(self.fonte(pt, negrito, italico))
        self.p.drawText(self.r(x, y, w, h), alinhar | Qt.AlignVCenter | Qt.TextWordWrap,
                        conteudo)

    def altura_do_texto(self, largura: float, conteudo: str, pt: float) -> float:
        self.p.setFont(self.fonte(pt))
        caixa = self.p.boundingRect(self.r(0, 0, largura, 200), Qt.TextWordWrap, conteudo)
        return caixa.height() / MM

    def linha(self, y: float, cor="#222222", espessura=0.3) -> None:
        self.p.setPen(QPen(QColor(cor), espessura * MM))
        self.p.drawLine(QPointF(MARGEM * MM, y * MM), QPointF((MARGEM + LARGURA) * MM, y * MM))

    def cabe(self, altura: float) -> bool:
        return self.y + altura <= FIM_DA_PAGINA

    def nova_pagina(self) -> None:
        self._rodape()
        self.escritor.newPage()
        self.pagina += 1
        self.y = MARGEM

    def _rodape(self) -> None:
        self.texto(MARGEM, 297 - 10, LARGURA, 5, f"{self.rodape} · página {self.pagina}", 6.5,
                   cor="#777777", alinhar=Qt.AlignHCenter, italico=True)

    def terminar(self) -> None:
        self._rodape()
        self.p.end()


def _imagem_do_grafico(definicao, resultado, largura_mm: float, altura_mm: float) -> QImage:
    """O gráfico desenhado pelo Matplotlib, em cores de papel, como imagem."""
    from matplotlib.backends.backend_agg import FigureCanvasAgg
    from matplotlib.figure import Figure

    from calibracao.interface.desenho_grafico import PAPEL, desenhar

    figura = Figure(figsize=(largura_mm / 25.4 * 1.55, altura_mm / 25.4 * 1.55), dpi=200)
    desenhar(figura, definicao, resultado, cores=PAPEL, estreito=True,
             titulo=definicao.titulo or ind.titulo_automatico(definicao))
    tela = FigureCanvasAgg(figura)
    tela.draw()
    largura, altura = tela.get_width_height()
    return QImage(bytes(tela.buffer_rgba()), largura, altura, QImage.Format_RGBA8888).copy()


def gerar_pdf(conteudo: ConteudoRelatorio, graficos: list[ind.DefinicaoGrafico],
              calibracoes: list[ind.CalibracaoParaIndicador],
              instrumentos: list[ind.InstrumentoParaIndicador], destino: Path) -> Path:
    """Escreve o PDF em `destino` e devolve o caminho. O do ano tem só os números do topo e os
    gráficos do painel (pedido do usuário em 2026-11-10); o do mês tem também as calibrações e as
    ALTERAÇÕES."""
    anual = conteudo.periodo.tipo != MENSAL
    folha = _Folha(destino, "DQ-05 Calibração de Instrumentos · MG Centro de Serviços")
    f = folha
    # --- cabeçalho
    f.texto(MARGEM, f.y, LARGURA, 8, f"DQ-05 CALIBRAÇÃO DE INSTRUMENTOS — {conteudo.titulo}",
            13, True)
    f.texto(MARGEM, f.y + 8, LARGURA, 5, conteudo.subtitulo, 7.5, cor="#555555")
    f.linha(f.y + 14)
    f.y += 17
    # --- números (quantidade de calibrações e custos)
    numeros = conteudo.numeros
    quantos = max(len(numeros), 1)
    largura = (LARGURA - 2 * (quantos - 1)) / quantos
    for n, numero in enumerate(numeros):
        x = MARGEM + n * (largura + 2)
        f.p.setPen(QPen(QColor("#9e9e9e"), 0.25 * MM))
        f.p.setBrush(Qt.NoBrush)
        f.p.drawRoundedRect(f.r(x, f.y, largura, 15), 1.2 * MM, 1.2 * MM)
        f.texto(x, f.y + 0.5, largura, 4, numero.rotulo, 6, cor="#555555",
                alinhar=Qt.AlignHCenter)
        f.texto(x, f.y + 5, largura, 9, numero.valor, 10 if len(numero.valor) > 6 else 15, True,
                CORES_NUMERO[numero.cor], alinhar=Qt.AlignHCenter)
    if numeros:
        f.y += 19
    # --- gráficos do painel (2 por linha)
    inicio = conteudo.periodo.inicio
    for posicao, definicao in enumerate(graficos):
        if posicao % 2 == 0:
            if posicao and not f.cabe(2 * ALTURA_GRAFICO + 2):  # a próxima fileira não cabe
                f.nova_pagina()
            elif posicao:
                f.y += ALTURA_GRAFICO + 2
        resultado = ind.calcular(definicao, calibracoes, instrumentos, conteudo.referencia,
                                 intervalo=(inicio, conteudo.referencia))
        x = MARGEM + (posicao % 2) * (LARGURA / 2 + 1)
        largura = LARGURA / 2 - 1
        f.p.setPen(QPen(QColor("#d0d0d0"), 0.25 * MM))
        f.p.setBrush(Qt.NoBrush)
        f.p.drawRect(f.r(x, f.y, largura, ALTURA_GRAFICO))
        f.p.drawImage(f.r(x + 0.5, f.y + 0.5, largura - 1, ALTURA_GRAFICO - 1),
                      _imagem_do_grafico(definicao, resultado, largura, ALTURA_GRAFICO))
    if graficos:
        f.y += ALTURA_GRAFICO + 5
    if anual:
        if not graficos:
            f.texto(MARGEM + 1, f.y, LARGURA, 5, "O painel da aba Indicadores está vazio.", 7.5,
                    cor="#555555", italico=True)
        f.terminar()
        return destino
    # --- tabela das calibrações
    nome = "Calibrações do mês" if conteudo.periodo.tipo == MENSAL else "Calibrações do ano"
    if not f.cabe(7 + 2 * ALTURA_LINHA):
        f.nova_pagina()
    f.texto(MARGEM, f.y, LARGURA, 6, nome, 10, True)
    f.y += 7
    _cabecalho_da_tabela(f)
    if not conteudo.linhas:
        f.texto(MARGEM + 1, f.y, LARGURA, ALTURA_LINHA, "Nenhuma calibração prevista ou feita "
                "no período.", 7, cor="#555555", italico=True)
        f.y += ALTURA_LINHA
    for linha in conteudo.linhas:
        if not f.cabe(ALTURA_LINHA):
            f.nova_pagina()
            _cabecalho_da_tabela(f)
        x = MARGEM
        valores = [linha.codigo, linha.tipo, linha.localizacao, linha.feita_em,
                   linha.certificado, linha.laboratorio, linha.situacao, linha.custo]
        for (titulo, largura), valor in zip(COLUNAS, valores, strict=True):
            if titulo.startswith("Parecer"):
                fundo, letra = FAIXAS.get(valor, ("#ffffff", "#111111"))
                f.p.setPen(Qt.NoPen)
                f.p.setBrush(QColor(fundo))
                f.p.drawRect(f.r(x, f.y + 0.3, largura, ALTURA_LINHA - 0.6))
                f.texto(x + 1, f.y, largura - 1, ALTURA_LINHA, valor, 6.8,
                        valor == "Orientação indicativa", letra)
            else:
                f.texto(x + 1, f.y, largura - 1, ALTURA_LINHA, _cortado(valor, largura), 6.8)
            x += largura
        f.linha(f.y + ALTURA_LINHA, "#cccccc", 0.15)
        f.y += ALTURA_LINHA
    # --- ALTERAÇÕES
    f.y += 5
    if not f.cabe(13):
        f.nova_pagina()
    f.texto(MARGEM, f.y, LARGURA, 6, "ALTERAÇÕES", 10, True)
    f.y += 7
    if not conteudo.alteracoes:
        f.texto(MARGEM + 1, f.y, LARGURA, 5, "Nenhuma alteração no período.", 7.5,
                cor="#555555", italico=True)
    for tipo, frase in conteudo.alteracoes:
        altura = max(5.0, f.altura_do_texto(LARGURA - 6, frase, 7.5) + 0.8)
        if not f.cabe(altura):
            f.nova_pagina()
        simbolo, cor = SIMBOLO[tipo]
        f.texto(MARGEM + 1, f.y, 5, 5, simbolo, 8, True, cor)
        f.texto(MARGEM + 6, f.y, LARGURA - 6, altura, frase, 7.5)
        f.y += altura + 0.3
    f.terminar()
    return destino


def _cabecalho_da_tabela(f: _Folha) -> None:
    f.p.setBrush(QColor("#222222"))
    f.p.setPen(Qt.NoPen)
    f.p.drawRect(f.r(MARGEM, f.y, LARGURA, ALTURA_LINHA))
    x = MARGEM
    for titulo, largura in COLUNAS:
        f.texto(x + 1, f.y, largura, ALTURA_LINHA, titulo, 6.6, True, "#ffffff")
        x += largura
    f.y += ALTURA_LINHA


def _cortado(texto: str, largura_mm: float) -> str:
    """Corta o texto que não cabe na coluna (≈ 0,95 mm por letra no tamanho da tabela)."""
    cabe = max(4, int(largura_mm / 1.15))
    return texto if len(texto) <= cabe else texto[:cabe - 1] + "…"


def nome_temporario(periodo_chave: str) -> Path:
    import tempfile

    agora = datetime.datetime.now().strftime("%H%M%S")
    return Path(tempfile.gettempdir()) / f"DQ-05 Relatório {periodo_chave} (atual {agora}).pdf"
