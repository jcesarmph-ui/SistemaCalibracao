"""Gráfico de tendência (Matplotlib dentro da janela), igual ao da planilha do usuário.

Aprovado por foto em 2026-11-10:

- **Eixo X = os pontos calibrados**, na ordem do plano (rótulo = descrição do ponto);
  **eixo Y = desvio final** — a mesma conta da tabela (`regras.avaliacao.desvio_final`: desvio
  ± U do lado mais perto da tolerância; desvio zero → +U). Sem barrinha da incerteza.
- **Cada calibração é uma linha, uma cor por ano** (duas no mesmo ano = mesma cor, outro
  marcador, legenda com a data). Clicar na legenda esconde/mostra a calibração. Os pontos de cada
  calibração ficam um pouquinho para o lado, para não se cobrirem.
- **Tolerância = linha cinza cheia** de ponta a ponta (degrau onde muda de um ponto a outro).
  Reprovado = anel vermelho (vermelho só para problema, como no resto do programa).
- **Seções**: seção com vários pontos = um gráfico grande (um embaixo do outro); seção com um
  ponto só = gráfico pequeno embaixo, ano a ano, com a faixa da tolerância pintada. Plano sem
  seção = um gráfico só. Pontos qualitativos não entram (o repositório já os deixa de fora).
"""

from dataclasses import dataclass
from pathlib import Path

import matplotlib

matplotlib.use("QtAgg")

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg  # noqa: E402
from matplotlib.figure import Figure  # noqa: E402
from matplotlib.lines import Line2D  # noqa: E402
from matplotlib.patches import Patch  # noqa: E402
from matplotlib.ticker import FuncFormatter  # noqa: E402
from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import (  # noqa: E402
    QDialog,
    QFileDialog,
    QHBoxLayout,
    QPushButton,
    QScrollArea,
    QVBoxLayout,
)

from calibracao.dados.repositorio import MedicaoTendencia, SerieTendencia  # noqa: E402
from calibracao.interface.componentes import (  # noqa: E402
    RotuloAviso,
    formatar_data,
)
from calibracao.interface.estilo import CORES, tema_claro  # noqa: E402
from calibracao.interface.painel_plano import numero_em_texto  # noqa: E402
from calibracao.interface.tema_icones import por_icone  # noqa: E402
from calibracao.regras.avaliacao import Resultado  # noqa: E402

# Uma cor por ano, bem diferentes entre si e sempre na mesma ordem (pedido de 2026-11-04).
# Sem vermelho, que marca o reprovado. Passando de 17 anos a cor se repete com outro marcador.
CORES_ANOS = [
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

# Tema claro: as mesmas cores, trocando as que somem no fundo claro por tons escuros.
TROCA_NO_CLARO = {"#ffe119": "#c9a400", "#42d4f4": "#0097a7", "#bfef45": "#7cb342",
                  "#f5f5f5": "#212121", "#fabed4": "#d81b60", "#dcbeff": "#6a1b9a",
                  "#ffd8b1": "#e65100", "#aaffc3": "#00897b", "#fffac8": "#5d4037"}

ALTURA_GRANDE = 430   # px de cada gráfico grande (seção com vários pontos)
ALTURA_PEQUENO = 300  # px de cada linha de gráficos pequenos
POR_LINHA = 3         # gráficos pequenos lado a lado
ESPACO_LADO = 0.32    # quanto as calibrações de um ponto se espalham para os lados (de 1)


def cor_e_marcador(indice: int) -> tuple[str, str]:
    cores = CORES_ANOS
    if tema_claro():
        cores = [TROCA_NO_CLARO.get(cor, cor) for cor in CORES_ANOS]
    return cores[indice % len(cores)], MARCADORES[indice // len(cores) % len(MARCADORES)]


def _texto(valor: float) -> str:
    return f"{round(valor, 6):g}".replace("-", "−").replace(".", ",")


@dataclass(frozen=True)
class Calibracao:
    """Uma calibração no gráfico: cor do ano dela e nome na legenda."""

    chave: tuple
    data: object
    cor: str
    marcador: str
    rotulo: str


@dataclass
class _Desenhado:
    """Um marcador na tela, para a dica do mouse."""

    eixo: object
    x: float
    y: float
    serie: SerieTendencia
    medicao: MedicaoTendencia
    calibracao: int


def _chave(m: MedicaoTendencia) -> tuple:
    return (m.data, m.calibracao_id)


def calibracoes_do_grafico(series: list[SerieTendencia]) -> list[Calibracao]:
    """Calibrações em ordem de data; cor pelo ano (mesmo ano = mesma cor, outro marcador)."""
    chaves = sorted({_chave(m) for s in series for m in s.medicoes},
                    key=lambda c: (c[0], c[1] or 0))
    anos = sorted({c[0].year for c in chaves})
    por_ano: dict[int, int] = {}
    for chave in chaves:
        por_ano[chave[0].year] = por_ano.get(chave[0].year, 0) + 1
    vistos: dict[int, int] = {}
    resultado = []
    for chave in chaves:
        ano = chave[0].year
        repetido = vistos.get(ano, 0)
        vistos[ano] = repetido + 1
        cor, marcador = cor_e_marcador(anos.index(ano))
        if repetido:
            marcador = MARCADORES[repetido % len(MARCADORES)]
        rotulo = formatar_data(chave[0]) if por_ano[ano] > 1 else str(ano)
        resultado.append(Calibracao(chave, chave[0], cor, marcador, rotulo))
    return resultado


def separar_por_secao(series: list[SerieTendencia]) -> tuple[list[tuple[str | None, list]],
                                                             list[SerieTendencia]]:
    """Seções com vários pontos (gráficos grandes) e pontos sozinhos na seção (pequenos).

    Plano sem seção conta como uma seção só. Se o plano inteiro tem um ponto só, ele vira um
    gráfico pequeno (ano a ano), que é o que faz sentido para um ponto.
    """
    secoes: dict[str | None, list[SerieTendencia]] = {}
    for serie in series:
        secoes.setdefault(serie.secao, []).append(serie)
    grandes = [(secao, lista) for secao, lista in secoes.items() if len(lista) > 1]
    pequenos = [lista[0] for lista in secoes.values() if len(lista) == 1]
    return grandes, pequenos


def _tolerancias(serie: SerieTendencia) -> tuple[float | None, float | None]:
    """Tolerância da calibração mais recente do ponto (a "foto" de cada uma fica na dica)."""
    ultima = serie.medicoes[-1]
    return ultima.tolerancia_inferior, ultima.tolerancia_superior


def _y(m: MedicaoTendencia) -> float:
    """Desvio final; sem ele (U ausente, raro: não dá para salvar assim), o desvio encontrado."""
    return m.final if m.final is not None else m.erro


def _faixa(inferior: float | None, superior: float | None) -> str:
    if inferior is not None and superior is not None and abs(inferior) == abs(superior):
        return f"± {numero_em_texto(abs(superior))}"
    return " a ".join(numero_em_texto(v) for v in (inferior, superior) if v is not None)


class JanelaTendencia(QDialog):
    def __init__(self, series: list[SerieTendencia], codigo: str, parent=None) -> None:
        super().__init__(parent)
        self.series = series
        self.codigo = codigo
        self.setWindowTitle(f"Gráfico de tendência — {codigo}")
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self.setWindowState(Qt.WindowMaximized)

        self.exportar = QPushButton("Salvar imagem (PNG)")
        por_icone(self.exportar, "download", CORES["titulo"])
        self.exportar.clicked.connect(self._escolher_arquivo)
        self.exportar.setEnabled(bool(series))
        fechar = QPushButton("Fechar")
        fechar.clicked.connect(self.accept)
        topo = QHBoxLayout()
        topo.addStretch(1)
        topo.addWidget(self.exportar)
        topo.addWidget(fechar)

        self.figura = Figure(figsize=(12, 6), facecolor=CORES["caixa"])
        self.tela = FigureCanvasQTAgg(self.figura)
        self.tela.mpl_connect("motion_notify_event", self._passou_o_mouse)
        self.tela.mpl_connect("pick_event", self._clicou_na_legenda)
        # Muitos gráficos (várias seções): a figura cresce e a janela ganha rolagem.
        self.rolagem = QScrollArea(widgetResizable=True)
        self.rolagem.setWidget(self.tela)
        self.aviso = RotuloAviso(objectName="dica", wordWrap=True)

        coluna = QVBoxLayout(self)
        coluna.addLayout(topo)
        coluna.addWidget(self.rolagem, 1)
        coluna.addWidget(self.aviso)
        self.desenhar()

    # ------------------------------------------------------------------ desenho

    def desenhar(self) -> None:
        self.figura.clear()
        self.eixos: list = []
        self._desenhados: list[_Desenhado] = []
        self._grupos: dict[int, list] = {}          # calibração → o que foi desenhado dela
        self._na_legenda: dict[object, int] = {}
        self._itens_legenda: dict[int, tuple] = {}
        self._dicas: dict[object, object] = {}
        self.escondidos: set[int] = set()
        if not self.series:
            eixo = self.figura.add_subplot(facecolor=CORES["caixa"])
            eixo.set_axis_off()
            eixo.text(0.5, 0.5, "Ainda não há pontos numéricos medidos para o gráfico.",
                      ha="center", va="center", color=CORES["texto"], fontsize=14,
                      transform=eixo.transAxes)
            self.aviso.setText("")
            self.tela.draw_idle()
            return

        self.calibracoes = calibracoes_do_grafico(self.series)
        self._indice = {c.chave: i for i, c in enumerate(self.calibracoes)}
        grandes, pequenos = separar_por_secao(self.series)
        linhas_pequenas = -(-len(pequenos) // POR_LINHA)
        alturas = [ALTURA_GRANDE] * len(grandes) + [ALTURA_PEQUENO] * linhas_pequenas
        topo_px, baixo_px = 100, 20  # topo: o título geral, sem encostar no 1º gráfico
        total = sum(alturas) + topo_px + baixo_px + 40 * len(alturas)
        self.tela.setMinimumHeight(total)
        self.figura.set_size_inches(self.figura.get_figwidth(), total / self.figura.dpi)

        grade = self.figura.add_gridspec(
            len(alturas), POR_LINHA if pequenos else 1, height_ratios=alturas,
            left=0.07, right=0.82, top=1 - topo_px / total, bottom=baixo_px / total + 0.02,
            hspace=0.55, wspace=0.3)
        self.figura.suptitle(f"Tendência — {self.codigo}", color=CORES["texto"], fontsize=16,
                             fontweight="bold", y=1 - 20 / total)
        algum_reprovado = False
        for linha, (secao, series) in enumerate(grandes):
            eixo = self.figura.add_subplot(grade[linha, :])
            algum_reprovado |= self._desenhar_grande(eixo, secao, series, linha == 0)
        for n, serie in enumerate(pequenos):
            eixo = self.figura.add_subplot(grade[len(grandes) + n // POR_LINHA, n % POR_LINHA])
            algum_reprovado |= self._desenhar_pequeno(eixo, serie, n % POR_LINHA == 0)
        self._legenda(algum_reprovado, bool(pequenos))
        self.aviso.setText(
            "Cada calibração é uma linha, uma cor por ano. O ponto é o desvio final (desvio "
            "encontrado ± Incerteza (U), do lado mais perto da tolerância). Clique no ano na "
            "legenda para esconder ou mostrar a calibração. Passe o mouse sobre um ponto para "
            "ver os valores.")
        self.tela.draw_idle()

    def _enfeitar(self, eixo, unidade: str | None, com_titulo_y: bool) -> None:
        eixo.set_facecolor(CORES["caixa"])
        eixo.axhline(0, color=CORES["campo_borda"], linewidth=1, zorder=1)
        eixo.tick_params(colors=CORES["texto"], labelsize=11)
        eixo.grid(True, axis="y", color=CORES["campo_borda"], linewidth=0.8, alpha=0.6)
        eixo.yaxis.set_major_formatter(FuncFormatter(lambda v, _: _texto(v)))
        for lado in eixo.spines.values():
            lado.set_color(CORES["campo_borda"])
        if com_titulo_y:
            fim = f" ({unidade})" if unidade else ""
            eixo.set_ylabel(f"Desvio final{fim}", color=CORES["texto"], fontsize=12)
        dica = eixo.annotate("", xy=(0, 0), xytext=(12, 12), textcoords="offset points",
                             color=CORES["texto"], fontsize=11, zorder=10,
                             bbox={"boxstyle": "round", "fc": CORES["campo"],
                                   "ec": CORES["borda"]})
        dica.set_visible(False)
        self._dicas[eixo] = dica
        self.eixos.append(eixo)

    def _guardar(self, indice: int, *artistas) -> None:
        self._grupos.setdefault(indice, []).extend(artistas)

    def _anel(self, eixo, x: float, y: float, indice: int, tamanho: int) -> None:
        self._guardar(indice, eixo.scatter([x], [y], s=tamanho, facecolors="none",
                                           edgecolors=CORES["erro"], linewidths=2, zorder=5))

    def _desenhar_grande(self, eixo, secao: str | None, series: list[SerieTendencia],
                         primeiro: bool) -> bool:
        """Seção com vários pontos: eixo X = pontos, uma linha por calibração."""
        unidade = series[0].unidade
        self._enfeitar(eixo, unidade, True)
        n = len(series)
        # tolerância: linha cheia de ponta a ponta, em degrau onde muda de um ponto ao outro
        tolerancias = [_tolerancias(s) for s in series]
        for lado in (0, 1):
            xs, ys = [], []
            for i, tol in enumerate(tolerancias):
                valor = tol[lado]
                xs += [i - 0.5, i + 0.5]
                ys += [valor if valor is not None else float("nan")] * 2
            xs[0], xs[-1] = -0.6, n - 0.4
            eixo.plot(xs, ys, color=CORES["dica"], linewidth=1.6, zorder=2)
        quantas = len(self.calibracoes)
        passo = ESPACO_LADO / max(quantas - 1, 1) if quantas > 1 else 0
        algum_reprovado = False
        for indice, calibracao in enumerate(self.calibracoes):
            desloc = (indice - (quantas - 1) / 2) * passo
            xs, ys = [], []
            for i, serie in enumerate(series):
                for m in serie.medicoes:
                    if _chave(m) != calibracao.chave:
                        continue
                    x, y = i + desloc, _y(m)
                    xs.append(x)
                    ys.append(y)
                    self._desenhados.append(_Desenhado(eixo, x, y, serie, m, indice))
                    if m.resultado == Resultado.REPROVADO:
                        algum_reprovado = True
                        self._anel(eixo, x, y, indice, 190)
            if not xs:
                continue
            self._guardar(indice, *eixo.plot(xs, ys, color=calibracao.cor, linewidth=2,
                                             zorder=3))
            self._guardar(indice, eixo.scatter(xs, ys, s=50, color=calibracao.cor,
                                               marker=calibracao.marcador,
                                               edgecolors=CORES["caixa"], linewidths=1.5,
                                               zorder=4))
        rotulos = [s.descricao or s.nome for s in series]
        eixo.set_xticks(range(n), rotulos, rotation=45 if n > 10 else 0,
                        ha="right" if n > 10 else "center")
        eixo.set_xlim(-0.6, n - 0.4)
        eixo.margins(y=0.15)
        fim = f" ({unidade})" if unidade else ""
        eixo.set_xlabel(f"Ponto calibrado{fim}", color=CORES["texto"], fontsize=12)
        comuns = set(tolerancias)
        titulo = secao or "Todas as calibrações"
        if secao:
            titulo += " — todas as calibrações"
        if len(comuns) == 1 and any(t is not None for t in tolerancias[0]):
            titulo += f" (tol. {_faixa(*tolerancias[0])})"
        eixo.set_title(titulo, color=CORES["texto"], fontsize=14, fontweight="bold")
        return algum_reprovado

    def _desenhar_pequeno(self, eixo, serie: SerieTendencia, primeiro_da_linha: bool) -> bool:
        """Ponto sozinho na seção: ano a ano, com a faixa da tolerância pintada."""
        self._enfeitar(eixo, serie.unidade, primeiro_da_linha)
        inferior, superior = _tolerancias(serie)
        if inferior is not None and superior is not None:
            eixo.axhspan(inferior, superior, color=CORES["dentro"],
                         alpha=0.3 if tema_claro() else 0.55, zorder=0)
        for valor in (inferior, superior):
            if valor is not None:
                eixo.axhline(valor, color=CORES["dica"], linewidth=1.6, zorder=2)
        posicoes = {c.chave: i for i, c in enumerate(self.calibracoes)
                    if any(_chave(m) == c.chave for m in serie.medicoes)}
        ordem = sorted(posicoes, key=lambda c: posicoes[c])
        algum_reprovado = False
        for m in serie.medicoes:
            indice = self._indice[_chave(m)]
            calibracao = self.calibracoes[indice]
            x, y = ordem.index(_chave(m)), _y(m)
            self._guardar(indice, eixo.scatter([x], [y], s=70, color=calibracao.cor,
                                               marker=calibracao.marcador,
                                               edgecolors=CORES["caixa"], linewidths=1.5,
                                               zorder=4))
            self._desenhados.append(_Desenhado(eixo, x, y, serie, m, indice))
            if m.resultado == Resultado.REPROVADO:
                algum_reprovado = True
                self._anel(eixo, x, y, indice, 230)
        eixo.set_xticks(range(len(ordem)),
                        [self.calibracoes[self._indice[c]].rotulo for c in ordem])
        eixo.set_xlim(-0.6, len(ordem) - 0.4)
        limites = [abs(v) for v in (inferior, superior) if v is not None]
        valores = [abs(_y(m)) for m in serie.medicoes]
        if limites:
            topo = max(max(limites) * 1.8, max(valores) * 1.25)
            eixo.set_ylim(-topo, topo)
        else:
            eixo.margins(y=0.3)
        titulo = " — ".join(t for t in (serie.secao, serie.descricao) if t) or serie.nome
        if serie.unidade:
            titulo += f" {serie.unidade}"
        if limites:
            titulo += f" (tol. {_faixa(inferior, superior)})"
        eixo.set_title(titulo, color=CORES["texto"], fontsize=12, fontweight="bold")
        return algum_reprovado

    def _legenda(self, algum_reprovado: bool, com_faixa: bool) -> None:
        itens = [Line2D([], [], color=c.cor, marker=c.marcador, linewidth=2, markersize=7,
                        label=c.rotulo) for c in self.calibracoes]
        itens.append(Line2D([], [], color=CORES["dica"], linewidth=1.6, label="Tolerância"))
        if com_faixa:
            itens.append(Patch(facecolor=CORES["dentro"], alpha=0.3 if tema_claro() else 0.55,
                               label="Dentro da tolerância"))
        if algum_reprovado:
            itens.append(Line2D([], [], color=CORES["erro"], marker="o", linestyle="",
                                markerfacecolor="none", markeredgewidth=2, markersize=11,
                                label="Reprovado"))
        primeiro = self.eixos[0].get_position()
        caixa = self.figura.legend(
            handles=itens, loc="upper left", bbox_to_anchor=(0.835, primeiro.y1),
            fontsize=11, facecolor=CORES["caixa"], edgecolor=CORES["campo_borda"],
            labelcolor=CORES["texto"], title="Calibração\n(clique para esconder)",
            title_fontsize=11)
        caixa.get_title().set_color(CORES["texto"])
        self.caixa_legenda = caixa
        # Clicar no ano (ou no traço) esconde/mostra a calibração.
        for indice, (linha, texto) in enumerate(zip(caixa.get_lines(), caixa.get_texts(),
                                                    strict=False)):
            if indice >= len(self.calibracoes):
                break
            self._itens_legenda[indice] = (linha, texto)
            for item in (linha, texto):
                item.set_picker(True)
                self._na_legenda[item] = indice

    # ------------------------------------------------------------------ interação

    def esconder_ou_mostrar(self, indice: int) -> None:
        """Calibração escondida fica apagada na legenda; clicar de novo mostra."""
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

    def texto_da_dica(self, desenhado: _Desenhado) -> str:
        m = desenhado.medicao
        linhas = [desenhado.serie.nome, formatar_data(m.data),
                  f"Desvio encontrado: {numero_em_texto(m.erro)}",
                  f"Incerteza (U): {numero_em_texto(m.incerteza) or '—'}"]
        if m.final is not None:
            linhas.append(f"Desvio final: {numero_em_texto(m.final)}")
        linhas.append(m.resultado.value)
        return "\n".join(linhas)

    def _passou_o_mouse(self, evento) -> None:
        """Dica com ponto, data, desvio, U, desvio final e resultado do marcador mais perto."""
        if not self._desenhados:
            return
        perto = None
        for desenhado in self._desenhados:
            if desenhado.eixo is not evento.inaxes or desenhado.calibracao in self.escondidos:
                continue
            x, y = desenhado.eixo.transData.transform((desenhado.x, desenhado.y))
            if abs(x - evento.x) < 10 and abs(y - evento.y) < 10:
                perto = desenhado
                break
        mudou = False
        for eixo, dica in self._dicas.items():
            if dica.get_visible() and (perto is None or eixo is not perto.eixo):
                dica.set_visible(False)
                mudou = True
        if perto is not None:
            dica = self._dicas[perto.eixo]
            dica.xy = (perto.x, perto.y)
            dica.set_text(self.texto_da_dica(perto))
            dica.set_visible(True)
            mudou = True
        if mudou:
            self.tela.draw_idle()

    # ------------------------------------------------------------------ imagem

    def salvar_png(self, caminho: Path) -> None:
        for dica in self._dicas.values():  # a dica do mouse não vai para a imagem
            dica.set_visible(False)
        self.figura.savefig(caminho, format="png", dpi=150, facecolor=CORES["caixa"],
                            bbox_inches="tight")

    def _escolher_arquivo(self) -> None:
        nome = f"tendencia_{self.codigo}.png"
        caminho, _ = QFileDialog.getSaveFileName(self, "Salvar gráfico", nome,
                                                 "Imagem PNG (*.png)")
        if caminho:
            self.salvar_png(Path(caminho))
            self.aviso.setText(f"✔ Imagem salva em {caminho}")
