"""Janela principal: cabeçalho, faixa de indicadores e abas de trabalho.

Layout em faixas (padrão MG): cabeçalho; indicadores (caixas iguais); abas Instrumentos,
Cronograma, Desativados e Lixeira. Tudo o que é dado vem do `Repositorio`.
"""

import datetime
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QPixmap
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QMainWindow,
    QTableWidget,
    QTableWidgetItem,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from calibracao import __version__
from calibracao.dados.repositorio import LinhaCronograma, Repositorio
from calibracao.interface.estilo import (
    CORES,
    CORES_RESULTADO,
    CORES_SITUACAO,
    estilo,
    resultado_em_html,
)
from calibracao.regras.avaliacao import Resultado
from calibracao.regras.cronograma import Situacao

TITULO = "CALIBRAÇÃO DE INSTRUMENTOS"

# (texto do indicador, dica ao passar o mouse)
INDICADORES = {
    "instrumentos": ("Instrumentos", "Instrumentos ativos (fora da Lixeira e não desativados)."),
    "calibracoes": ("Calibrações", "Calibrações registradas no programa."),
    "vencidas": ("Vencidas", "A data prevista da próxima calibração já passou."),
    "proximas": ("Próximos 30 dias", "Calibração prevista de hoje até daqui a 30 dias."),
    "sem_calibracao": ("Sem calibração no programa",
                       "Ainda não tiveram nenhuma calibração registrada no programa."),
}

FILTROS_CRONOGRAMA = ["Todos", *[s.value for s in Situacao]]


def formatar_data(data: datetime.date | None) -> str:
    return data.strftime("%d/%m/%Y") if data else "—"


def celula(texto: str, cores: tuple[str, str] | None = None) -> QTableWidgetItem:
    item = QTableWidgetItem(texto)
    item.setFlags(Qt.ItemIsEnabled | Qt.ItemIsSelectable)
    if cores:
        item.setBackground(QColor(cores[0]))
        item.setForeground(QColor(cores[1]))
        item.setTextAlignment(Qt.AlignCenter)
    return item


class JanelaPrincipal(QMainWindow):
    def __init__(self, repositorio: Repositorio, pasta_dados: Path,
                 hoje: datetime.date | None = None) -> None:
        super().__init__()
        self.repo = repositorio
        self.pasta_dados = pasta_dados
        self.hoje = hoje or datetime.date.today()
        self.valores_indicadores: dict[str, QLabel] = {}

        self.setWindowTitle(
            f"Calibração de Instrumentos — MG Centro de Serviços — versão {__version__}"
        )
        self.setStyleSheet(estilo())

        self.abas = QTabWidget()
        self.abas.addTab(self._aba_em_construcao("o cadastro de instrumentos, planos e "
                                                 "calibrações"), "Instrumentos")
        self.abas.addTab(self._aba_cronograma(), "Cronograma")
        self.abas.addTab(self._aba_em_construcao("os instrumentos desativados"), "Desativados")
        self.abas.addTab(self._aba_em_construcao("a Lixeira"), "Lixeira")
        self.abas.setCurrentIndex(1)

        tela = QVBoxLayout()
        tela.addLayout(self._cabecalho())
        tela.addLayout(self._faixa_indicadores())
        tela.addWidget(self.abas, 1)
        central = QWidget(objectName="central")
        central.setLayout(tela)
        self.setCentralWidget(central)

        self.atualizar()

    # --- Montagem da tela -------------------------------------------------------------------

    def _cabecalho(self) -> QGridLayout:
        """Logo à esquerda, título centralizado na largura toda, versão à direita."""
        arquivo_logo = self.pasta_dados / "logo_mg.png"
        if arquivo_logo.is_file():
            logo = QLabel()
            logo.setPixmap(QPixmap(str(arquivo_logo)).scaledToHeight(80, Qt.SmoothTransformation))
        else:
            logo = QLabel("MG Centro de Serviços")
        grade = QGridLayout()
        grade.addWidget(logo, 0, 0, Qt.AlignLeft)
        grade.addWidget(QLabel(TITULO, objectName="titulo"), 0, 1)
        grade.addWidget(QLabel(f"versão {__version__}", objectName="dica"), 0, 2,
                        Qt.AlignRight | Qt.AlignBottom)
        grade.setColumnStretch(0, 1)
        grade.setColumnStretch(2, 1)  # coluna do mesmo tamanho da do logo → título no centro
        return grade

    def _faixa_indicadores(self) -> QHBoxLayout:
        faixa = QHBoxLayout()
        for chave, (texto, dica) in INDICADORES.items():
            caixa = QGroupBox(texto)
            caixa.setToolTip(dica)
            valor = QLabel("0", objectName="indicador", alignment=Qt.AlignCenter)
            QVBoxLayout(caixa).addWidget(valor)
            self.valores_indicadores[chave] = valor
            faixa.addWidget(caixa, 1)
        return faixa

    def _aba_cronograma(self) -> QWidget:
        self.filtro_cronograma = QComboBox()
        self.filtro_cronograma.addItems(FILTROS_CRONOGRAMA)
        self.filtro_cronograma.currentTextChanged.connect(self._preencher_cronograma)
        topo = QHBoxLayout()
        topo.addWidget(QLabel("Mostrar:"))
        topo.addWidget(self.filtro_cronograma)
        topo.addStretch()
        self.contagem_cronograma = QLabel(objectName="dica")
        topo.addWidget(self.contagem_cronograma)

        colunas = ["Código", "Tipo", "Localização", "Última calibração", "Próxima calibração",
                   "Situação", "Resultado da última"]
        self.tabela_cronograma = QTableWidget(0, len(colunas))
        self.tabela_cronograma.setHorizontalHeaderLabels(colunas)
        self.tabela_cronograma.verticalHeader().setVisible(False)
        self.tabela_cronograma.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela_cronograma.setEditTriggers(QAbstractItemView.NoEditTriggers)
        cabecalho = self.tabela_cronograma.horizontalHeader()
        cabecalho.setSectionResizeMode(QHeaderView.Stretch)
        cabecalho.setSectionResizeMode(0, QHeaderView.ResizeToContents)

        aba = QWidget()
        caixa = QVBoxLayout(aba)
        caixa.addLayout(topo)
        caixa.addWidget(self.tabela_cronograma)
        return aba

    @staticmethod
    def _aba_em_construcao(oque: str) -> QWidget:
        aba = QWidget()
        caixa = QVBoxLayout(aba)
        caixa.addWidget(QLabel(f"Em construção: aqui ficará {oque}.", objectName="dica",
                               alignment=Qt.AlignCenter))
        return aba

    # --- Dados ------------------------------------------------------------------------------

    def atualizar(self) -> None:
        """Relê o banco e redesenha indicadores e tabelas."""
        self._cronograma = self.repo.cronograma(self.hoje)
        contagem = {s: 0 for s in Situacao}
        for linha in self._cronograma:
            contagem[linha.situacao] += 1
        valores = {
            "instrumentos": len(self.repo.listar_instrumentos()),
            "calibracoes": self.repo.contar_calibracoes(),
            "vencidas": contagem[Situacao.VENCIDA],
            "proximas": contagem[Situacao.PROXIMOS_30_DIAS],
            "sem_calibracao": contagem[Situacao.SEM_CALIBRACAO],
        }
        cor_se_houver = {"vencidas": CORES["erro"], "proximas": CORES["aviso"],
                         "sem_calibracao": CORES["aviso"]}
        for chave, valor in valores.items():
            rotulo = self.valores_indicadores[chave]
            rotulo.setText(str(valor))
            cor = cor_se_houver.get(chave) if valor else None
            rotulo.setStyleSheet(f"color: {cor};" if cor else "")
        self._preencher_cronograma(self.filtro_cronograma.currentText())

    def _preencher_cronograma(self, filtro: str) -> None:
        linhas: list[LinhaCronograma] = [
            linha for linha in self._cronograma if filtro == "Todos" or linha.situacao == filtro
        ]
        tabela = self.tabela_cronograma
        tabela.setRowCount(len(linhas))
        for indice, linha in enumerate(linhas):
            instrumento = linha.instrumento
            resultado = linha.resultado_ultima
            valores = [
                celula(instrumento.codigo),
                celula(instrumento.tipo),
                celula(instrumento.localizacao or "—"),
                celula(formatar_data(linha.ultima)),
                celula(formatar_data(linha.proxima)),
                celula(linha.situacao.value, CORES_SITUACAO[linha.situacao]),
                celula(resultado.value, CORES_RESULTADO.get(resultado))
                if resultado and resultado != Resultado.APROVADO_INDICATIVO
                else celula("—" if resultado is None else ""),
            ]
            for coluna, item in enumerate(valores):
                tabela.setItem(indice, coluna, item)
            tabela.removeCellWidget(indice, 6)
            if resultado == Resultado.APROVADO_INDICATIVO:
                # Só as palavras "orientação indicativa" com a cor da etiqueta física.
                valores[6].setText("")
                tabela.setCellWidget(indice, 6, QLabel(resultado_em_html(resultado),
                                                       alignment=Qt.AlignCenter))
        self.contagem_cronograma.setText(f"{len(linhas)} instrumento(s)")
