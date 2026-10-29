"""Gráfico de tendência (Matplotlib dentro da janela), como no protótipo, com exportar PNG.

Um ponto do plano por vez (escolhido na lista): o erro de cada calibração (medido − nominal, ou o
erro do certificado) com a barra da Incerteza (U), e a tolerância em linhas tracejadas. Ponto
reprovado ganha marcador vermelho — vermelho só para problema, como no resto do programa.
"""

from pathlib import Path

import matplotlib

matplotlib.use("QtAgg")

import matplotlib.dates as mdates  # noqa: E402
from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QComboBox,
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QVBoxLayout,
)

from calibracao.dados.repositorio import SerieTendencia  # noqa: E402
from calibracao.interface.componentes import formatar_data  # noqa: E402
from calibracao.interface.estilo import CORES  # noqa: E402
from calibracao.interface.painel_plano import numero_em_texto  # noqa: E402
from calibracao.regras.avaliacao import Resultado  # noqa: E402

# Cores do gráfico no tema escuro: série em azul (1ª cor da paleta categórica validada para fundo
# escuro), tolerância em cinza (recessiva), reprovado no vermelho de erro do programa.
COR_SERIE = "#3987e5"
COR_TOLERANCIA = "#9e9e9e"
COR_REPROVADO = CORES["erro"]
COR_TEXTO = "#f0f0f0"
COR_GRADE = "#3a3a3a"
COR_FUNDO = CORES["caixa"]


class JanelaTendencia(QDialog):
    def __init__(self, series: list[SerieTendencia], codigo: str, parent=None) -> None:
        super().__init__(parent)
        self.series = series
        self.codigo = codigo
        self.setWindowTitle(f"Gráfico de tendência — {codigo}")
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self.setWindowState(Qt.WindowMaximized)

        self.ponto = QComboBox()
        for serie in series:
            self.ponto.addItem(f"{serie.nome} ({len(serie.medicoes)} calibração(ões))")
        self.ponto.currentIndexChanged.connect(self.desenhar)
        self.exportar = QPushButton("Salvar imagem (PNG)…")
        self.exportar.clicked.connect(self._escolher_arquivo)
        self.exportar.setEnabled(bool(series))
        fechar = QPushButton("Fechar")
        fechar.clicked.connect(self.accept)
        topo = QHBoxLayout()
        topo.addWidget(QLabel("Ponto do plano:"))
        topo.addWidget(self.ponto, 1)
        topo.addWidget(self.exportar)
        topo.addWidget(fechar)

        self.figura = Figure(figsize=(12, 6), facecolor=COR_FUNDO)
        self.tela = FigureCanvasQTAgg(self.figura)
        self.tela.mpl_connect("motion_notify_event", self._passou_o_mouse)
        self.aviso = QLabel(objectName="dica", wordWrap=True)

        coluna = QVBoxLayout(self)
        coluna.addLayout(topo)
        coluna.addWidget(self.tela, 1)
        coluna.addWidget(self.aviso)
        self.desenhar()

    def desenhar(self) -> None:
        self.figura.clear()
        eixo = self.figura.add_subplot(facecolor=COR_FUNDO)
        self._eixo = eixo
        self._pontos_desenhados = []
        if not self.series:
            eixo.set_axis_off()
            eixo.text(0.5, 0.5, "Ainda não há pontos numéricos medidos para o gráfico.",
                      ha="center", va="center", color=COR_TEXTO, fontsize=14,
                      transform=eixo.transAxes)
            self.aviso.setText("")
            self.tela.draw_idle()
            return
        serie = self.series[self.ponto.currentIndex()]
        medicoes = serie.medicoes
        unidade = f" {serie.unidade}" if serie.unidade else ""
        datas = [m.data for m in medicoes]
        erros = [m.erro for m in medicoes]
        barras = [m.incerteza or 0.0 for m in medicoes]

        eixo.errorbar(datas, erros, yerr=barras, color=COR_SERIE, linewidth=2, marker="o",
                      markersize=8, capsize=6, elinewidth=1.5, zorder=3,
                      markeredgecolor=COR_FUNDO, markeredgewidth=2)
        reprovados = [m for m in medicoes if m.resultado == Resultado.REPROVADO]
        if reprovados:
            eixo.scatter([m.data for m in reprovados], [m.erro for m in reprovados], s=110,
                         color=COR_REPROVADO, edgecolors=COR_FUNDO, linewidths=2, zorder=4)
        # Tolerância da calibração mais recente (a "foto" de cada uma fica no tooltip).
        ultima = medicoes[-1]
        for valor, nome in ((ultima.tolerancia_superior, "Tol. superior"),
                            (ultima.tolerancia_inferior, "Tol. inferior")):
            if valor is not None:
                eixo.axhline(valor, color=COR_TOLERANCIA, linestyle="--", linewidth=1.5)
                eixo.annotate(f"{nome} {numero_em_texto(valor)}", xy=(1, valor),
                              xycoords=("axes fraction", "data"), xytext=(-6, 4),
                              textcoords="offset points", ha="right", color=COR_TEXTO,
                              fontsize=10)
        eixo.axhline(0, color=COR_GRADE, linewidth=1)
        self._pontos_desenhados = medicoes

        eixo.set_title(f"Tendência — {self.codigo} — {serie.nome}", color=COR_TEXTO,
                       fontsize=15, fontweight="bold", pad=12)
        eixo.set_ylabel(f"Erro{unidade}", color=COR_TEXTO, fontsize=12)
        eixo.set_xlabel("Data da calibração", color=COR_TEXTO, fontsize=12)
        eixo.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%Y"))
        eixo.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=8))
        eixo.yaxis.set_major_formatter(FuncFormatter(  # vírgula decimal, como no Brasil
            lambda valor, _: f"{valor:g}".replace("-", "−").replace(".", ",")))
        eixo.margins(x=0.15, y=0.25)
        eixo.tick_params(colors=COR_TEXTO, labelsize=11)
        eixo.grid(True, color=COR_GRADE, linewidth=0.8, alpha=0.6)
        for lado in eixo.spines.values():
            lado.set_color(COR_GRADE)
        legenda = [Line2D([], [], color=COR_SERIE, marker="o", linewidth=2,
                          label="Erro medido ± Incerteza (U)"),
                   Line2D([], [], color=COR_TOLERANCIA, linestyle="--", label="Tolerância")]
        if reprovados:
            legenda.append(Line2D([], [], color=COR_REPROVADO, marker="o", linestyle="",
                                  markersize=9, label="Ponto reprovado"))
        eixo.legend(handles=legenda, loc="upper left", fontsize=10, facecolor=COR_FUNDO,
                    edgecolor=COR_GRADE, labelcolor=COR_TEXTO)
        self.figura.autofmt_xdate()
        self.figura.tight_layout()

        self._dica = eixo.annotate("", xy=(0, 0), xytext=(12, 12), textcoords="offset points",
                                   color=COR_TEXTO, fontsize=11,
                                   bbox={"boxstyle": "round", "fc": "#161616", "ec": "#e0e0e0"})
        self._dica.set_visible(False)
        self.aviso.setText("Passe o mouse sobre um ponto para ver os valores. A barra vertical "
                           "é a Incerteza (U): o ponto só é aprovado se a barra inteira ficar "
                           "dentro da tolerância.")
        self.tela.draw_idle()

    def _passou_o_mouse(self, evento) -> None:
        """Tooltip com data, erro, U e resultado do ponto mais perto do mouse."""
        if not self._pontos_desenhados or evento.inaxes is not self._eixo:
            return
        perto = None
        for medicao in self._pontos_desenhados:
            x, y = self._eixo.transData.transform((mdates.date2num(medicao.data), medicao.erro))
            if abs(x - evento.x) < 12 and abs(y - evento.y) < 12:
                perto = medicao
                break
        visivel = self._dica.get_visible()
        if perto is None:
            if visivel:
                self._dica.set_visible(False)
                self.tela.draw_idle()
            return
        u = numero_em_texto(perto.incerteza) or "—"
        self._dica.xy = (mdates.date2num(perto.data), perto.erro)
        self._dica.set_text(f"{formatar_data(perto.data)}\nErro: {numero_em_texto(perto.erro)}"
                            f"\nIncerteza (U): {u}\n{perto.resultado.value}")
        self._dica.set_visible(True)
        self.tela.draw_idle()

    def salvar_png(self, caminho: Path) -> None:
        if self._pontos_desenhados:
            self._dica.set_visible(False)  # a dica do mouse não vai para a imagem
        self.figura.savefig(caminho, format="png", dpi=180, facecolor=COR_FUNDO,
                            bbox_inches="tight")

    def _escolher_arquivo(self) -> None:
        nome = f"tendencia_{self.codigo}_ponto{self.ponto.currentIndex() + 1}.png"
        caminho, _ = QFileDialog.getSaveFileName(self, "Salvar gráfico", nome,
                                                 "Imagem PNG (*.png)")
        if caminho:
            self.salvar_png(Path(caminho))
            self.aviso.setText(f"✔ Imagem salva em {caminho}")
