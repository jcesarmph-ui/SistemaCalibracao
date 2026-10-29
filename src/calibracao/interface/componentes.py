"""Peças de tela usadas em mais de uma aba."""

import datetime

from PySide6.QtCore import QPoint, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QFrame,
    QGroupBox,
    QHeaderView,
    QLabel,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from calibracao.interface.estilo import destacar_indicativa, tem_orientacao_indicativa


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


def aplicar_destaques(tabela: QTableWidget) -> None:
    """Em toda célula com "orientação indicativa", essas palavras ganham a cor da etiqueta.

    O texto continua no item (busca e testes), só fica invisível embaixo do rótulo colorido.
    """
    for linha in range(tabela.rowCount()):
        for coluna in range(tabela.columnCount()):
            item = tabela.item(linha, coluna)
            tabela.removeCellWidget(linha, coluna)
            if item is None or not tem_orientacao_indicativa(item.text()):
                continue
            item.setForeground(QColor(0, 0, 0, 0))
            rotulo = QLabel(destacar_indicativa(item.text()))
            rotulo.setAlignment(Qt.AlignVCenter | (Qt.AlignHCenter if item.textAlignment()
                                                   & Qt.AlignHCenter else Qt.AlignLeft))
            rotulo.setContentsMargins(3, 0, 3, 0)
            tabela.setCellWidget(linha, coluna, rotulo)


def tabela_somente_leitura(colunas: list[str]) -> QTableWidget:
    tabela = QTableWidget(0, len(colunas))
    tabela.setHorizontalHeaderLabels(colunas)
    tabela.verticalHeader().setVisible(False)
    tabela.setSelectionBehavior(QAbstractItemView.SelectRows)
    tabela.setEditTriggers(QAbstractItemView.NoEditTriggers)
    cabecalho = tabela.horizontalHeader()
    cabecalho.setSectionResizeMode(QHeaderView.Stretch)
    cabecalho.setSectionResizeMode(0, QHeaderView.ResizeToContents)
    return tabela


class PainelClicavel(QGroupBox):
    """Caixa de indicador que responde ao clique (abre a lista flutuante)."""

    clicado = Signal()

    def __init__(self, titulo: str) -> None:
        super().__init__(titulo)
        self.setCursor(Qt.PointingHandCursor)

    def mousePressEvent(self, evento) -> None:  # noqa: N802 — nome exigido pelo Qt
        if evento.button() == Qt.LeftButton:
            self.clicado.emit()
        super().mousePressEvent(evento)


class ListaFlutuante(QFrame):
    """Janelinha que "sai" de um painel, como um tooltip grande; fecha ao clicar fora."""

    def __init__(self, titulo: str, colunas: list[str], linhas: list[list[QTableWidgetItem]],
                 parent: QWidget) -> None:
        super().__init__(parent, Qt.Popup)
        self.setObjectName("flutuante")
        self.setStyleSheet("#flutuante { background: #0a0a0a; border: 1px solid #e0e0e0; "
                           "border-radius: 6px; }")
        tabela = tabela_somente_leitura(colunas)
        tabela.setRowCount(len(linhas))
        for indice, itens in enumerate(linhas):
            for coluna, item in enumerate(itens):
                tabela.setItem(indice, coluna, item)
        aplicar_destaques(tabela)
        # Colunas do tamanho do conteúdo (nada cortado); a largura é medida ao abrir, já com o tema.
        tabela.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        tabela.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        self._tabela = tabela
        caixa = QVBoxLayout(self)
        caixa.addWidget(QLabel(f"<b>{titulo}</b>"))
        if linhas:
            caixa.addWidget(tabela)
            altura = tabela.horizontalHeader().height() + sum(
                tabela.rowHeight(i) for i in range(len(linhas))) + 4
            tabela.setFixedHeight(min(altura, 420))
        else:
            caixa.addWidget(QLabel("Nenhum instrumento.", objectName="dica"))
        caixa.addWidget(QLabel("Clique fora para fechar.", objectName="dica"))

    def mostrar_abaixo_de(self, painel: QWidget) -> None:
        self.ensurePolished()
        self._tabela.ensurePolished()
        self._tabela.resizeColumnsToContents()
        colunas = range(self._tabela.columnCount())
        largura_tabela = (sum(self._tabela.columnWidth(c) for c in colunas)
                          + self._tabela.verticalScrollBar().sizeHint().width() + 4)
        self._tabela.setMinimumWidth(largura_tabela)
        self.setMinimumWidth(max(painel.width(), largura_tabela + 24))
        self.adjustSize()
        posicao = painel.mapToGlobal(QPoint(0, painel.height() + 4))
        tela = painel.screen().availableGeometry()
        posicao.setX(min(posicao.x(), tela.right() - self.width()))  # não sai da tela à direita
        self.move(posicao)
        self.show()
