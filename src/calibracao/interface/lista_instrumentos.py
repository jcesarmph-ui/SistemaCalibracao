"""Lista de instrumentos com filtros e busca — a mesma nas abas Instrumentos e Calibrar.

Só o código é clicável (pedido do usuário em 2026-11-03): ele funciona como um botão — clareia
com o mouse por cima e, clicado, avisa a aba (`escolhido`), que mostra os dados do instrumento.
As outras colunas só mostram: não clareiam e não respondem ao clique.
"""

from PySide6.QtCore import QEvent, QModelIndex, Qt, Signal
from PySide6.QtGui import QBrush, QColor
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QTableWidget,
    QVBoxLayout,
)

from calibracao.dados.repositorio import Instrumento, MudancaCondicao
from calibracao.interface.componentes import (
    aplicar_destaques,
    celula,
    formatar_data,
    preenchendo,
)
from calibracao.interface.estilo import CORES, CORES_CONDICAO, CORES_SITUACAO
from calibracao.regras.condicao import Condicao
from calibracao.regras.localizacao import eh_indicativa
from calibracao.regras.padronizacao import (
    chave,
    locais,
    ordem,
    preferidas_dos_locais,
    preferidas_dos_tipos,
    tipo_padrao,
)

# Filtro "Condição" da lista: condições mostradas em cada opção (pedido do usuário em 2026-10-29).
# A lista abre na primeira; os desativados só aparecem escolhendo o filtro. "Orientação
# indicativa" não é condição (pedido de 2026-11-03): mostra os não desativados com a marca.
FILTROS_CONDICAO = {
    "Todos menos desativados": (Condicao.EM_USO,),
    "Em uso": (Condicao.EM_USO,),
    "Orientação indicativa": (Condicao.EM_USO,),
    "Desativados": (Condicao.DESATIVADO,),
    "Todos": tuple(Condicao),
}
SO_INDICATIVA = "Orientação indicativa"
TODOS_OS_TIPOS = "Todos os tipos"
TODAS_AS_LOCALIZACOES = "Todas as localizações"
DICA_CODIGO = "Clique para abrir os dados deste instrumento."


class ListaInstrumentos(QGroupBox):
    escolhido = Signal(int)  # id do instrumento clicado

    def __init__(self) -> None:
        super().__init__("Instrumentos")
        self.situacoes: dict = {}  # id do instrumento → situação no cronograma
        self.condicoes: dict[int, MudancaCondicao] = {}
        self.instrumentos: list[Instrumento] = []
        self.atual_id: int | None = None
        self._tipo_de: dict[int, str] = {}
        self._locais_de: dict[int, set[str]] = {}

        self.filtro_condicao = QComboBox()
        self.filtro_condicao.addItems(FILTROS_CONDICAO)
        self.filtro_condicao.setToolTip("Mostrar só os instrumentos nesta condição.")
        self.filtro_tipo = QComboBox()
        self.filtro_tipo.setToolTip("Ex.: escolha Paquímetro para ver todos os paquímetros.")
        self.filtro_local = QComboBox()
        for filtro in (self.filtro_condicao, self.filtro_tipo, self.filtro_local):
            filtro.currentTextChanged.connect(self.preencher)
        self.busca = QLineEdit(placeholderText="Buscar por código, tipo ou localização")
        self.busca.textChanged.connect(self.preencher)

        colunas = ["Código", "Localização", "Condição", "Desde", "Situação"]
        self.tabela = QTableWidget(0, len(colunas))
        self.tabela.setHorizontalHeaderLabels(colunas)
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabela.setEditTriggers(QAbstractItemView.NoEditTriggers)
        cabecalho = self.tabela.horizontalHeader()
        cabecalho.setSectionResizeMode(QHeaderView.ResizeToContents)
        cabecalho.setSectionResizeMode(1, QHeaderView.Stretch)  # quem se ajusta é a localização
        self.tabela.itemSelectionChanged.connect(self._selecionou)
        # Só o código é clicável: clareia com o mouse (como um botão) e tem a mãozinha.
        self.tabela.setMouseTracking(True)
        self.tabela.entered.connect(self._mouse_sobre)
        self.tabela.viewport().installEventFilter(self)
        self._clareado = None  # célula de código que está clareada pelo mouse
        self.contagem = QLabel(objectName="dica")

        filtros = QHBoxLayout()
        filtros.addWidget(self.filtro_condicao, 1)
        filtros.addWidget(self.filtro_tipo, 1)
        filtros.addWidget(self.filtro_local, 1)
        coluna = QVBoxLayout(self)
        coluna.addLayout(filtros)
        coluna.addWidget(self.busca)
        coluna.addWidget(self.tabela)
        coluna.addWidget(self.contagem)

    def atualizar(self, instrumentos: list[Instrumento],
                  condicoes: dict[int, MudancaCondicao], situacoes: dict) -> None:
        """Recarrega a lista (mantendo filtros e o instrumento escolhido)."""
        self.instrumentos, self.condicoes, self.situacoes = instrumentos, condicoes, situacoes
        # Um nome só para cada tipo e cada local; instrumento em "Serralheria / Manutenção"
        # aparece nos dois locais (pedido de 2026-11-10).
        tipos = preferidas_dos_tipos(i.tipo for i in instrumentos)
        self._tipo_de = {i.id: chave(tipo_padrao(i.tipo, tipos) or "") for i in instrumentos}
        self._locais_de = {i.id: {chave(local) for local in locais(i.localizacao)}
                           for i in instrumentos}
        self._recarregar_opcoes(self.filtro_tipo, TODOS_OS_TIPOS, set(tipos.values()))
        self._recarregar_opcoes(
            self.filtro_local, TODAS_AS_LOCALIZACOES,
            set(preferidas_dos_locais(i.localizacao for i in instrumentos).values()))
        self.preencher()

    @staticmethod
    def _recarregar_opcoes(filtro: QComboBox, todos: str, opcoes: set[str]) -> None:
        """Repõe as opções do filtro mantendo a escolha atual (se ela ainda existir)."""
        escolhido = filtro.currentText()
        filtro.blockSignals(True)
        filtro.clear()
        filtro.addItems([todos, *sorted(opcoes, key=ordem)])
        filtro.setCurrentText(escolhido if escolhido in opcoes else todos)
        filtro.blockSignals(False)

    def condicao(self, instrumento_id: int) -> MudancaCondicao:
        return self.condicoes.get(instrumento_id, MudancaCondicao(Condicao.EM_USO, None))

    def visiveis(self) -> list[Instrumento]:
        termo = self.busca.text().strip().lower()
        condicoes = FILTROS_CONDICAO[self.filtro_condicao.currentText()]
        tipo = self.filtro_tipo.currentText()
        local = self.filtro_local.currentText()
        return [
            i for i in self.instrumentos
            if self.condicao(i.id).condicao in condicoes
            and (self.filtro_condicao.currentText() != SO_INDICATIVA
                 or eh_indicativa(i.localizacao))
            and (tipo == TODOS_OS_TIPOS or self._tipo_de.get(i.id) == chave(tipo))
            and (local == TODAS_AS_LOCALIZACOES or chave(local) in self._locais_de.get(i.id, ()))
            and (not termo or termo in f"{i.codigo} {i.tipo} {i.localizacao or ''}".lower())
        ]

    def preencher(self) -> None:
        self._clareado = None
        visiveis = self.visiveis()
        with preenchendo(self.tabela):  # rápido: ajusta as colunas uma vez só
            self.tabela.blockSignals(True)
            self.tabela.setRowCount(len(visiveis))
            for linha, instrumento in enumerate(visiveis):
                condicao = self.condicao(instrumento.id)
                situacao = self.situacoes.get(instrumento.id)
                if situacao:
                    item_situacao = celula(situacao.value, CORES_SITUACAO[situacao])
                elif condicao.condicao == Condicao.DESATIVADO:
                    item_situacao = celula("Fora do cronograma")
                else:
                    item_situacao = celula("Não precisa de calibração")
                itens = [celula(instrumento.codigo), celula(instrumento.localizacao or "—"),
                         celula(condicao.condicao.value, CORES_CONDICAO[condicao.condicao]),
                         celula(formatar_data(condicao.data)), item_situacao]
                itens[0].setData(Qt.UserRole, instrumento.id)
                itens[0].setToolTip(f"{instrumento.tipo} — {DICA_CODIGO}")
                for coluna, item in enumerate(itens):
                    self.tabela.setItem(linha, coluna, item)
                if instrumento.id == self.atual_id:
                    self.tabela.selectRow(linha)
            aplicar_destaques(self.tabela)
        self.tabela.blockSignals(False)
        self.contagem.setText(f"{len(visiveis)} de {len(self.instrumentos)} instrumento(s)")

    def _mouse_sobre(self, indice: QModelIndex) -> None:
        """Sobre o código: clareia e mostra a mãozinha (é por ele que se abre o instrumento)."""
        self._apagar_clareado()
        if indice.column() == 0:
            item = self.tabela.item(indice.row(), 0)
            item.setBackground(QColor(CORES["mouse"]))
            self._clareado = item
            self.tabela.viewport().setCursor(Qt.PointingHandCursor)
        else:
            self.tabela.viewport().setCursor(Qt.ArrowCursor)

    def _apagar_clareado(self) -> None:
        if self._clareado is not None:
            try:
                self._clareado.setBackground(QBrush())
            except RuntimeError:  # a lista foi refeita e a célula já não existe
                pass
            self._clareado = None

    def eventFilter(self, objeto, evento) -> bool:  # noqa: N802 — nome exigido pelo Qt
        """Clique fora do código não faz nada; o mouse saindo da lista apaga o clareado."""
        tipo = evento.type()
        if tipo == QEvent.Leave:
            self._apagar_clareado()
        elif tipo in (QEvent.MouseButtonPress, QEvent.MouseButtonDblClick,
                      QEvent.MouseButtonRelease):
            indice = self.tabela.indexAt(evento.position().toPoint())
            if indice.isValid() and indice.column() != 0:
                return True
        return super().eventFilter(objeto, evento)

    def marcar(self, instrumento_id: int | None) -> None:
        """Guarda qual está aberto (a linha continua selecionada ao recarregar)."""
        self.atual_id = instrumento_id
        if instrumento_id is None:
            self.tabela.clearSelection()

    def _selecionou(self) -> None:
        linhas = self.tabela.selectionModel().selectedRows()
        if not linhas:
            return
        self.atual_id = self.tabela.item(linhas[0].row(), 0).data(Qt.UserRole)
        self.escolhido.emit(self.atual_id)
