"""Peças de tela usadas em mais de uma aba."""

import datetime

from PySide6.QtCore import QEvent, QObject, QPoint, Qt, Signal
from PySide6.QtGui import QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QAbstractSpinBox,
    QApplication,
    QComboBox,
    QFrame,
    QGroupBox,
    QHeaderView,
    QLabel,
    QTabBar,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from calibracao.interface.estilo import destacar, tem_destaque


class FiltroRodaDoMouse(QObject):
    """A roda do mouse só rola a tela: nunca troca opção, data ou aba (pedido de 2026-10-30).

    Em cima de lista de opções, campo de data/número ou barra de abas, a rolagem vai para quem
    está por trás (a tabela ou a página), que sobe e desce normalmente.
    """

    SEM_RODA = (QComboBox, QAbstractSpinBox, QTabBar)

    def eventFilter(self, objeto, evento) -> bool:  # noqa: N802 — nome exigido pelo Qt
        if evento.type() == QEvent.Wheel and isinstance(objeto, self.SEM_RODA):
            pai = objeto.parentWidget()
            if pai is not None:
                QApplication.sendEvent(pai, evento)
            return True
        return False


def instalar_filtro_roda() -> None:
    """Liga o filtro para o programa inteiro (janelas e diálogos), uma vez só."""
    app = QApplication.instance()
    if app is not None and not hasattr(app, "_filtro_roda"):
        app._filtro_roda = FiltroRodaDoMouse(app)
        app.installEventFilter(app._filtro_roda)


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
    """Em toda célula com "orientação indicativa" ou "reserva", essas palavras ganham cor.

    O texto continua no item (busca e testes), só fica invisível embaixo do rótulo colorido.
    """
    for linha in range(tabela.rowCount()):
        for coluna in range(tabela.columnCount()):
            item = tabela.item(linha, coluna)
            antigo = tabela.cellWidget(linha, coluna)
            if antigo is not None:  # some já; o Qt só apaga o rótulo depois
                antigo.hide()
                tabela.removeCellWidget(linha, coluna)
            if item is None or not tem_destaque(item.text()):
                continue
            item.setForeground(QColor(0, 0, 0, 0))
            rotulo = QLabel(destacar(item.text()))
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


class RotuloClicavel(QLabel):
    """Texto que responde ao clique (ex.: o modo no canto, que pede a edição)."""

    clicado = Signal()

    def mousePressEvent(self, evento) -> None:  # noqa: N802 — nome exigido pelo Qt
        if evento.button() == Qt.LeftButton:
            self.clicado.emit()
        super().mousePressEvent(evento)


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
