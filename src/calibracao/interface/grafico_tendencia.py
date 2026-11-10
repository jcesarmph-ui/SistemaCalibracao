"""Gráfico de tendência (Matplotlib dentro da janela), como no protótipo, com exportar PNG.

Abre em **todos os pontos juntos** (pedido de 2026-11-03, item 17 do teste), um de cada cor; na
lista dá para escolher um ponto por vez. Em cada um: o desvio encontrado de cada calibração
(encontrado − exigido, ou o desvio do certificado) com a barra da Incerteza (U), e a tolerância em
linhas tracejadas.

Todos juntos: se todos os pontos têm a mesma tolerância, o eixo é o desvio (na unidade do ponto);
se não, é a **% da tolerância usada** (100% = no limite), para caber tudo num gráfico só. Todos os
pontos de uma calibração ficam na mesma reta vertical, na data dela (pedido de 2026-11-04).

Reprovado: vermelho (marcador no gráfico de um ponto, anel em volta no de todos) — vermelho só
para problema, como no resto do programa.
"""

from dataclasses import dataclass
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

from calibracao.dados.repositorio import MedicaoTendencia, SerieTendencia  # noqa: E402
from calibracao.interface.componentes import (
    RotuloAviso,
    formatar_data,  # noqa: E402
)
from calibracao.interface.estilo import CORES, tema_claro  # noqa: E402
from calibracao.interface.painel_plano import numero_em_texto  # noqa: E402
from calibracao.interface.tema_icones import por_icone
from calibracao.regras.avaliacao import Resultado  # noqa: E402

# Série em azul, tolerância em cinza (recessiva), reprovado no vermelho de erro do programa. O
# resto (texto, grade, fundo) vem do tema na hora de desenhar (modo claro/escuro, 2026-11-10).
COR_SERIE = "#3987e5"
# Todos juntos: 17 cores bem diferentes entre si (o maior plano tem 17 pontos), sempre na mesma
# ordem — nada de dois tons da mesma cor (pedido de 2026-11-04). Verde e amarelo podem aparecer:
# aqui cada cor é só um ponto, a legenda diz qual. Sem vermelho, que marca o reprovado. Só passando
# de 17 a cor se repete, com outro formato de marcador.
CORES_PONTOS = [
    "#3987e5",  # azul
    "#ff8c1a",  # laranja
    "#3cb44b",  # verde
    "#ffe119",  # amarelo
    "#f032e6",  # magenta
    "#42d4f4",  # ciano
    "#a05cf0",  # roxo
    "#bfef45",  # verde-limão
    "#f5f5f5",  # branco
    "#9a6324",  # marrom
    "#fabed4",  # rosa-claro
    "#469990",  # verde-azulado
    "#dcbeff",  # lavanda
    "#808000",  # oliva
    "#ffd8b1",  # pêssego
    "#aaffc3",  # menta
    "#fffac8",  # creme
]
MARCADORES = ["o", "s", "^", "D", "v", "P"]
TODOS = "Todos os pontos juntos"
MAXIMO_DE_DATAS = 12  # até aqui, cada data de calibração aparece embaixo do gráfico


# Tema claro: as mesmas cores, trocando as que somem no fundo claro por tons escuros.
TROCA_NO_CLARO = {"#ffe119": "#c9a400", "#42d4f4": "#0097a7", "#bfef45": "#7cb342",
                  "#f5f5f5": "#212121", "#fabed4": "#d81b60", "#dcbeff": "#6a1b9a",
                  "#ffd8b1": "#e65100", "#aaffc3": "#00897b", "#fffac8": "#5d4037"}


def cores_dos_pontos() -> list[str]:
    if tema_claro():
        return [TROCA_NO_CLARO.get(cor, cor) for cor in CORES_PONTOS]
    return CORES_PONTOS


def cor_e_marcador(indice: int) -> tuple[str, str]:
    return (cores_dos_pontos()[indice % len(CORES_PONTOS)],
            MARCADORES[indice // len(CORES_PONTOS) % len(MARCADORES)])


def _tolerancias(serie: SerieTendencia) -> tuple[float | None, float | None]:
    """Tolerância da calibração mais recente do ponto (a "foto" de cada uma fica na dica)."""
    ultima = serie.medicoes[-1]
    return ultima.tolerancia_inferior, ultima.tolerancia_superior


def tolerancia_comum(series: list[SerieTendencia]) -> bool:
    """Todos os pontos com a mesma tolerância e a mesma unidade → o eixo pode ser o erro."""
    tolerancias = {_tolerancias(s) for s in series}
    unidades = {s.unidade for s in series}
    return (len(tolerancias) == 1 and len(unidades) == 1
            and any(t is not None for t in next(iter(tolerancias))))


def em_porcentagem(valor: float, inferior: float | None, superior: float | None) -> float | None:
    """Erro em % da tolerância do seu lado (acima de zero, a superior; abaixo, a inferior).
    Faltando um lado, vale o tamanho do outro; sem nenhum, não dá para calcular (None)."""
    lado = superior if valor >= 0 else inferior
    if lado is None or lado == 0:
        lado = inferior if valor >= 0 else superior
    if lado is None or lado == 0:
        return None
    return valor / abs(lado) * 100


@dataclass
class _Desenhado:
    """Um marcador na tela, para a dica do mouse."""

    x: float
    y: float
    nome: str | None
    medicao: MedicaoTendencia
    porcentagem: float | None = None
    serie: int | None = None


def _texto(valor: float) -> str:
    return f"{valor:g}".replace("-", "−").replace(".", ",")


class JanelaTendencia(QDialog):
    def __init__(self, series: list[SerieTendencia], codigo: str, parent=None) -> None:
        super().__init__(parent)
        self.series = series
        self.codigo = codigo
        self.setWindowTitle(f"Gráfico de tendência — {codigo}")
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self.setWindowState(Qt.WindowMaximized)

        self.ponto = QComboBox()
        if len(series) > 1:  # o principal: é o primeiro a aparecer
            self.ponto.addItem(f"{TODOS} ({len(series)} pontos)", None)
        for indice, serie in enumerate(series):
            self.ponto.addItem(f"{serie.nome} ({len(serie.medicoes)} calibração(ões))", indice)
        self.ponto.currentIndexChanged.connect(self.desenhar)
        self.exportar = QPushButton("Salvar imagem (PNG)")
        por_icone(self.exportar, "download", CORES["titulo"])
        self.exportar.clicked.connect(self._escolher_arquivo)
        self.exportar.setEnabled(bool(series))
        fechar = QPushButton("Fechar")
        fechar.clicked.connect(self.accept)
        topo = QHBoxLayout()
        topo.addWidget(QLabel("Mostrar:"))
        topo.addWidget(self.ponto, 1)
        topo.addWidget(self.exportar)
        topo.addWidget(fechar)

        self.figura = Figure(figsize=(12, 6), facecolor=CORES["caixa"])
        self.tela = FigureCanvasQTAgg(self.figura)
        self.tela.mpl_connect("motion_notify_event", self._passou_o_mouse)
        self.tela.mpl_connect("pick_event", self._clicou_na_legenda)
        self.aviso = RotuloAviso(objectName="dica", wordWrap=True)

        coluna = QVBoxLayout(self)
        coluna.addLayout(topo)
        coluna.addWidget(self.tela, 1)
        coluna.addWidget(self.aviso)
        self.desenhar()

    @property
    def todos(self) -> bool:
        return bool(self.series) and self.ponto.currentData() is None

    def desenhar(self) -> None:
        self.figura.clear()
        eixo = self.figura.add_subplot(facecolor=CORES["caixa"])
        self._eixo = eixo
        self._desenhados: list[_Desenhado] = []
        # Todos juntos: o que foi desenhado de cada ponto, para esconder/mostrar pela legenda.
        self._grupos: dict[int, list] = {}
        self._na_legenda: dict[object, int] = {}
        self._itens_legenda: dict[int, tuple] = {}
        self.escondidos: set[int] = set()
        if not self.series:
            eixo.set_axis_off()
            eixo.text(0.5, 0.5, "Ainda não há pontos numéricos medidos para o gráfico.",
                      ha="center", va="center", color=CORES["texto"], fontsize=14,
                      transform=eixo.transAxes)
            self.aviso.setText("")
            self.tela.draw_idle()
            return
        if self.todos:
            self._desenhar_todos(eixo)
        else:
            self._desenhar_um(eixo, self.series[self.ponto.currentData()])
        eixo.axhline(0, color=CORES["campo_borda"], linewidth=1)
        eixo.set_xlabel("Data da calibração", color=CORES["texto"], fontsize=12)
        eixo.xaxis.set_major_formatter(mdates.DateFormatter("%d/%m/%Y"))
        # No eixo, as datas das próprias calibrações (pedido de 2026-11-04); com muitas, o
        # Matplotlib escolhe algumas para não encavalar.
        datas = sorted({d.x for d in self._desenhados})
        if len(datas) <= MAXIMO_DE_DATAS:
            eixo.set_xticks(datas)
        else:
            eixo.xaxis.set_major_locator(mdates.AutoDateLocator(maxticks=8))
        eixo.tick_params(colors=CORES["texto"], labelsize=11)
        eixo.grid(True, color=CORES["campo_borda"], linewidth=0.8, alpha=0.6)
        for lado in eixo.spines.values():
            lado.set_color(CORES["campo_borda"])
        self.figura.autofmt_xdate()
        self.figura.tight_layout()

        self._dica = eixo.annotate("", xy=(0, 0), xytext=(12, 12), textcoords="offset points",
                                   color=CORES["texto"], fontsize=11,
                                   bbox={"boxstyle": "round", "fc": CORES["campo"],
                                         "ec": CORES["borda"]})
        self._dica.set_visible(False)
        self.tela.draw_idle()

    def _desenhar_um(self, eixo, serie: SerieTendencia) -> None:
        medicoes = serie.medicoes
        unidade = f" {serie.unidade}" if serie.unidade else ""
        datas = [m.data for m in medicoes]
        erros = [m.erro for m in medicoes]
        barras = [m.incerteza or 0.0 for m in medicoes]

        eixo.errorbar(datas, erros, yerr=barras, color=COR_SERIE, linewidth=2, marker="o",
                      markersize=8, capsize=6, elinewidth=1.5, zorder=3,
                      markeredgecolor=CORES["caixa"], markeredgewidth=2)
        reprovados = [m for m in medicoes if m.resultado == Resultado.REPROVADO]
        if reprovados:
            eixo.scatter([m.data for m in reprovados], [m.erro for m in reprovados], s=110,
                         color=CORES["erro"], edgecolors=CORES["caixa"], linewidths=2, zorder=4)
        inferior, superior = _tolerancias(serie)
        self._linhas_de_tolerancia(eixo, inferior, superior, numero_em_texto)
        self._desenhados = [_Desenhado(mdates.date2num(m.data), m.erro, None, m)
                            for m in medicoes]

        eixo.set_title(f"Tendência — {self.codigo} — {serie.nome}", color=CORES["texto"],
                       fontsize=15, fontweight="bold", pad=12)
        eixo.set_ylabel(f"Desvio encontrado{unidade}", color=CORES["texto"], fontsize=12)
        eixo.yaxis.set_major_formatter(FuncFormatter(lambda v, _: _texto(v)))
        eixo.margins(x=0.15, y=0.25)
        legenda = [Line2D([], [], color=COR_SERIE, marker="o", linewidth=2,
                          label="Desvio encontrado ± Incerteza (U)"),
                   Line2D([], [], color=CORES["dica"], linestyle="--", label="Tolerância")]
        if reprovados:
            legenda.append(Line2D([], [], color=CORES["erro"], marker="o", linestyle="",
                                  markersize=9, label="Ponto reprovado"))
        eixo.legend(handles=legenda, loc="upper left", fontsize=10, facecolor=CORES["caixa"],
                    edgecolor=CORES["campo_borda"], labelcolor=CORES["texto"])
        self.aviso.setText("Passe o mouse sobre um ponto para ver os valores. A barra vertical "
                           "é a Incerteza (U): o ponto só é aprovado se a barra inteira ficar "
                           "dentro da tolerância.")

    def _desenhar_todos(self, eixo) -> None:
        comum = tolerancia_comum(self.series)
        legenda, sem_tolerancia, algum_reprovado = [], [], False
        for indice, serie in enumerate(self.series):
            cor, marcador = cor_e_marcador(indice)
            inferior, superior = _tolerancias(serie)
            xs, ys, baixo, cima, grupo = [], [], [], [], []
            for m in serie.medicoes:
                u = m.incerteza or 0.0
                if comum:
                    y, u_baixo, u_cima, pct = m.erro, u, u, None
                else:
                    pct = em_porcentagem(m.erro, m.tolerancia_inferior, m.tolerancia_superior)
                    if pct is None:
                        continue
                    y = pct
                    u_cima = abs(em_porcentagem(u, m.tolerancia_inferior,
                                                m.tolerancia_superior) or 0.0)
                    u_baixo = abs(em_porcentagem(-u, m.tolerancia_inferior,
                                                 m.tolerancia_superior) or 0.0)
                x = mdates.date2num(m.data)  # a calibração inteira na mesma vertical
                xs.append(x)
                ys.append(y)
                baixo.append(u_baixo)
                cima.append(u_cima)
                self._desenhados.append(_Desenhado(x, y, serie.nome, m, pct, indice))
                if m.resultado == Resultado.REPROVADO:
                    algum_reprovado = True
                    grupo.append(eixo.scatter([x], [y], s=190, facecolors="none",
                                              edgecolors=CORES["erro"], linewidths=2, zorder=5))
            if not xs:
                sem_tolerancia.append(serie.nome)
                continue
            grupo += eixo.plot(xs, ys, color=cor, linewidth=1.6, alpha=0.85, zorder=3)
            barras = eixo.errorbar(xs, ys, yerr=[baixo, cima], fmt="none", ecolor=cor,
                                   elinewidth=1.2, capsize=3, alpha=0.7, zorder=2)
            grupo += [*barras.lines[1], *barras.lines[2]]
            grupo.append(eixo.scatter(xs, ys, s=46, color=cor, marker=marcador,
                                      edgecolors=CORES["caixa"], linewidths=1.5, zorder=4))
            self._grupos[indice] = grupo
            nome = serie.nome
            if not comum and (inferior is not None or superior is not None):
                nome += f" (tol. {self._faixa(inferior, superior, serie.unidade)})"
            legenda.append(Line2D([], [], color=cor, marker=marcador, linewidth=1.6,
                                  markersize=7, label=nome))

        unidade = self.series[0].unidade
        if comum:
            inferior, superior = _tolerancias(self.series[0])
            self._linhas_de_tolerancia(eixo, inferior, superior, numero_em_texto)
            eixo.set_ylabel(f"Desvio encontrado {unidade}" if unidade
                            else "Desvio encontrado", color=CORES["texto"], fontsize=12)
            eixo.yaxis.set_major_formatter(FuncFormatter(lambda v, _: _texto(v)))
            explicacao = (f"Tolerância igual em todos os pontos "
                          f"({self._faixa(inferior, superior, unidade)}): eixo em desvio")
        else:
            self._linhas_de_tolerancia(eixo, -100, 100, lambda v: f"{_texto(v)}%")
            eixo.set_ylabel("Desvio em % da tolerância", color=CORES["texto"], fontsize=12)
            eixo.yaxis.set_major_formatter(FuncFormatter(lambda v, _: f"{_texto(v)}%"))
            explicacao = ("Tolerâncias diferentes entre os pontos: eixo em % da tolerância "
                          "usada (100% = no limite)")
        eixo.set_title(f"Tendência — {self.codigo} — todos os pontos\n{explicacao}",
                       color=CORES["texto"], fontsize=14, fontweight="bold", pad=12)
        eixo.margins(x=0.06, y=0.25)
        legenda.append(Line2D([], [], color=CORES["dica"], linestyle="--", label="Tolerância"))
        if algum_reprovado:
            legenda.append(Line2D([], [], color=CORES["erro"], marker="o", linestyle="",
                                  markerfacecolor="none", markeredgewidth=2, markersize=11,
                                  label="Reprovado"))
        caixa = eixo.legend(handles=legenda, loc="upper left", bbox_to_anchor=(1.01, 1),
                            fontsize=10, facecolor=CORES["caixa"], edgecolor=CORES["campo_borda"],
                            labelcolor=CORES["texto"], title="Ponto (clique para esconder)",
                            title_fontsize=11)
        caixa.get_title().set_color(CORES["texto"])
        # Clicar no nome (ou no traço) de um ponto na legenda esconde/mostra esse ponto.
        for indice, linha, texto in zip(self._grupos, caixa.get_lines(), caixa.get_texts(),
                                        strict=False):
            self._itens_legenda[indice] = (linha, texto)
            for item in (linha, texto):
                item.set_picker(True)
                self._na_legenda[item] = indice
        texto = ("Cada cor é um ponto do plano; os pontos de uma calibração ficam na mesma "
                 "vertical, na data dela. A barra vertical é a Incerteza (U). Clique no "
                 "nome de um ponto na legenda para escondê-lo ou mostrá-lo de novo. Passe o mouse "
                 "sobre um ponto para ver os valores; para ver um ponto sozinho, escolha-o em "
                 "\"Mostrar\".")
        if sem_tolerancia:
            texto += (" Sem tolerância, fora deste gráfico (veja-os sozinhos): "
                      + ", ".join(sem_tolerancia) + ".")
        self.aviso.setText(texto)

    def esconder_ou_mostrar(self, indice: int) -> None:
        """Ponto escondido fica apagado na legenda; clicar de novo mostra."""
        escondido = indice not in self.escondidos
        if escondido:
            self.escondidos.add(indice)
        else:
            self.escondidos.discard(indice)
        for artista in self._grupos.get(indice, []):
            artista.set_visible(not escondido)
        for item in self._itens_legenda.get(indice, ()):
            item.set_alpha(0.3 if escondido else 1.0)
        self.tela.draw_idle()

    def _clicou_na_legenda(self, evento) -> None:
        indice = self._na_legenda.get(evento.artist)
        if indice is not None:
            self.esconder_ou_mostrar(indice)

    @staticmethod
    def _faixa(inferior: float | None, superior: float | None, unidade: str | None) -> str:
        fim = f" {unidade}" if unidade else ""
        if inferior is not None and superior is not None and abs(inferior) == abs(superior):
            return f"± {numero_em_texto(abs(superior))}{fim}"
        partes = [numero_em_texto(v) for v in (inferior, superior) if v is not None]
        return " a ".join(partes) + fim

    @staticmethod
    def _linhas_de_tolerancia(eixo, inferior, superior, formato) -> None:
        for valor, nome in ((superior, "Tol. superior"), (inferior, "Tol. inferior")):
            if valor is not None:
                eixo.axhline(valor, color=CORES["dica"], linestyle="--", linewidth=1.5)
                eixo.annotate(f"{nome} {formato(valor)}", xy=(1, valor),
                              xycoords=("axes fraction", "data"), xytext=(-6, 4),
                              textcoords="offset points", ha="right", color=CORES["texto"],
                              fontsize=10)

    def _passou_o_mouse(self, evento) -> None:
        """Dica com ponto, data, desvio, U e resultado do marcador mais perto do mouse."""
        if not self._desenhados or evento.inaxes is not self._eixo:
            return
        perto = None
        for desenhado in self._desenhados:
            if desenhado.serie in self.escondidos:
                continue
            x, y = self._eixo.transData.transform((desenhado.x, desenhado.y))
            if abs(x - evento.x) < 10 and abs(y - evento.y) < 10:
                perto = desenhado
                break
        visivel = self._dica.get_visible()
        if perto is None:
            if visivel:
                self._dica.set_visible(False)
                self.tela.draw_idle()
            return
        m = perto.medicao
        linhas = [perto.nome] if perto.nome else []
        linhas += [formatar_data(m.data), f"Desvio encontrado: {numero_em_texto(m.erro)}"]
        if perto.porcentagem is not None:
            linhas[-1] += f" ({_texto(round(perto.porcentagem))}% da tolerância)"
        linhas += [f"Incerteza (U): {numero_em_texto(m.incerteza) or '—'}", m.resultado.value]
        self._dica.xy = (perto.x, perto.y)
        self._dica.set_text("\n".join(linhas))
        self._dica.set_visible(True)
        self.tela.draw_idle()

    def salvar_png(self, caminho: Path) -> None:
        if self._desenhados:
            self._dica.set_visible(False)  # a dica do mouse não vai para a imagem
        self.figura.savefig(caminho, format="png", dpi=180, facecolor=CORES["caixa"],
                            bbox_inches="tight")

    def _escolher_arquivo(self) -> None:
        final = "todos" if self.todos else f"ponto{(self.ponto.currentData() or 0) + 1}"
        nome = f"tendencia_{self.codigo}_{final}.png"
        caminho, _ = QFileDialog.getSaveFileName(self, "Salvar gráfico", nome,
                                                 "Imagem PNG (*.png)")
        if caminho:
            self.salvar_png(Path(caminho))
            self.aviso.setText(f"✔ Imagem salva em {caminho}")
