"""Desenha um gráfico de indicador (`regras.indicadores.ResultadoGrafico`) numa figura do
Matplotlib: na aba Indicadores (cores do tema) e no relatório em PDF (sempre claro, para
imprimir). Importar este arquivo carrega o Matplotlib: só quando um gráfico é mostrado.
"""

import matplotlib

matplotlib.use("QtAgg")
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.ticker import MaxNLocator  # noqa: E402

from calibracao.interface.estilo import CORES  # noqa: E402
from calibracao.regras import indicadores as ind  # noqa: E402

# Cores com significado (as mesmas do programa): verde certo, amarelo aviso, vermelho problema.
CORES_DAS_SERIES = {"Aprovado": "#43a047", "Orientação indicativa": "#f9a825",
                    "Reprovado - Desativado": "#e53935", ind.NO_PRAZO_TXT: "#43a047",
                    ind.COM_ATRASO_TXT: "#f9a825"}
AZUL = "#3987e5"
# Outras séries (ex.: laboratórios): cores bem diferentes, sem verde/amarelo/vermelho.
PALETA = [AZUL, "#ff8c1a", "#a05cf0", "#42d4f4", "#f032e6", "#9a6324", "#808000", "#469990"]
PAPEL = {"fundo": "#ffffff", "texto": "#222222", "grade": "#dddddd"}


class TelaDoGrafico(FigureCanvasQTAgg):
    """O gráfico na tela. A roda do mouse rola a página (o gráfico não "engole" a roda)."""

    def wheelEvent(self, evento):  # noqa: N802 — nome exigido pelo Qt
        evento.ignore()


def cores_da_tela() -> dict[str, str]:
    return {"fundo": CORES["caixa"], "texto": CORES["texto"], "grade": CORES["campo_borda"]}


def nova_figura(largura: float = 6.0, altura: float = 3.4) -> Figure:
    return Figure(figsize=(largura, altura))


def desenhar(figura: Figure, definicao: ind.DefinicaoGrafico, resultado: ind.ResultadoGrafico,
             cores: dict[str, str] | None = None, estreito: bool = False,
             titulo: str | None = None) -> None:
    """Desenha (ou escreve o aviso, se não há dados). `estreito`: prévia pequena do montador
    (nomes do eixo inclinam antes). `titulo`: escrito em cima (no PDF; na tela o título fica na
    caixa)."""
    cores = cores or cores_da_tela()
    fundo, texto, grade = cores["fundo"], cores["texto"], cores["grade"]
    figura.clear()
    figura.set_facecolor(fundo)
    eixo = figura.add_subplot()
    eixo.set_facecolor(fundo)
    eixo.tick_params(colors=texto, labelsize=8)
    for lado in eixo.spines.values():
        lado.set_color(grade)
    if titulo:
        figura.suptitle(titulo, color=texto, fontsize=9, fontweight="bold")
    if resultado.vazio:
        eixo.text(0.5, 0.5, resultado.aviso or "Sem dados", ha="center", va="center",
                  color=texto, fontsize=10, wrap=True, transform=eixo.transAxes)
        eixo.set_xticks([])
        eixo.set_yticks([])
        figura.tight_layout()
        return
    definicao = ind.ajustar(definicao)
    limite = definicao.medida == ind.PERTO_DO_LIMITE
    forma = definicao.forma
    deitado = forma == ind.DEITADAS
    eixo.grid(axis="x" if deitado else "y", color=grade, linewidth=0.5)
    eixo.set_axisbelow(True)
    categorias, series, unidade = resultado.categorias, resultado.series, resultado.unidade
    posicoes = list(range(len(categorias)))
    base = [0.0] * len(categorias)
    for n, (nome, valores) in enumerate(series.items()):
        if limite:  # vermelho = fora; amarelo = 90% ou mais; cinza = folgado
            cor = ["#e53935" if v > 100 else "#f9a825" if v >= 90 else "#90a4ae"
                   for v in valores]
        else:
            cor = CORES_DAS_SERIES.get(nome, PALETA[n % len(PALETA)])
        if forma == ind.LINHA:
            eixo.plot(posicoes, valores, marker="o", color=cor, linewidth=2, label=nome)
        elif deitado:
            eixo.barh(posicoes, valores, left=base, color=cor, label=nome)
        else:
            eixo.bar(posicoes, valores, bottom=base, color=cor, label=nome)
        if forma != ind.LINHA:
            base = [b + v for b, v in zip(base, valores, strict=True)]
    if forma != ind.LINHA and len(series) == 1:  # o número em cima de cada barra
        for p, v in zip(posicoes, base, strict=True):
            if not v:
                continue
            rotulo = (f"{v:,.0f}".replace(",", ".") if unidade == "R$"
                      else f"{v:.0f}%" if unidade == "%" else f"{v:g}")
            if deitado:
                eixo.text(v, p, f" {rotulo}", va="center", fontsize=7, color=texto)
            else:
                eixo.text(p, v, rotulo, ha="center", va="bottom", fontsize=7, color=texto)
    if limite:
        eixo.axvline(100, color="#e53935", linewidth=1)
    if unidade == "":  # quantidade: só números inteiros no eixo
        (eixo.xaxis if deitado else eixo.yaxis).set_major_locator(MaxNLocator(integer=True))
    if deitado:
        eixo.set_yticks(posicoes, categorias)
        eixo.invert_yaxis()
        eixo.margins(x=0.15)
    else:
        letras = sum(len(c) for c in categorias)
        girar = (len(categorias) > (6 if estreito else 12)
                 or letras > (40 if estreito else 90))
        eixo.set_xticks(posicoes, categorias, rotation=45 if girar else 0,
                        ha="right" if girar else "center")
        eixo.margins(y=0.15)
    if len(series) > 1:  # legenda fora, em cima: nunca cobre as barras
        eixo.legend(fontsize=7, labelcolor=texto, frameon=False, loc="lower center",
                    bbox_to_anchor=(0.5, 1.0), ncol=min(len(series), 4))
    if unidade:
        (eixo.set_xlabel if deitado else eixo.set_ylabel)(unidade, color=texto, fontsize=8)
    if resultado.nota:
        figura.text(0.99, 0.01, resultado.nota, ha="right", va="bottom", fontsize=7,
                    color=texto, style="italic")
    figura.tight_layout()
