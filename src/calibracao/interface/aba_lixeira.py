"""Aba Lixeira: o que foi enviado por engano. Restaurar devolve; excluir de vez apaga para sempre.

Regras (do protótipo, ver `calibracao.regras.lixeira`): restaurar exige o "pai" fora da Lixeira;
excluir de vez exige digitar EXCLUIR e não vale para item com registros ligados — exceto a
calibração, que vai embora junto com os seus pontos medidos.
"""

import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from calibracao.dados.repositorio import ErroDeValidacao, ItemLixeira, Repositorio
from calibracao.interface.componentes import celula, tabela_somente_leitura
from calibracao.interface.estilo import CORES
from calibracao.regras.lixeira import CONFIRMACAO_EXCLUSAO, Tipo

TODOS = "Tudo"
# Opções do filtro "Mostrar:" (texto no plural → tipo)
FILTROS = {TODOS: None, "Instrumentos": Tipo.INSTRUMENTO, "Planos": Tipo.PLANO,
           "Pontos do plano": Tipo.PONTO, "Calibrações": Tipo.CALIBRACAO}


def quando(texto_iso: str) -> str:
    """'2026-10-29T14:05:00' → '29/10/2026 14:05'."""
    return datetime.datetime.fromisoformat(texto_iso).strftime("%d/%m/%Y %H:%M")


class JanelaExcluir(QDialog):
    """Confirmação de exclusão permanente: só libera com EXCLUIR digitado."""

    def __init__(self, item: ItemLixeira, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle("Excluir permanentemente")
        self.confirmacao = QLineEdit(placeholderText=f"Digite {CONFIRMACAO_EXCLUSAO}")
        botoes = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.confirmar = botoes.button(QDialogButtonBox.Ok)
        self.confirmar.setText("Excluir para sempre")
        self.confirmar.setEnabled(False)
        botoes.button(QDialogButtonBox.Cancel).setText("Cancelar")
        self.confirmacao.textChanged.connect(
            lambda texto: self.confirmar.setEnabled(texto.strip() == CONFIRMACAO_EXCLUSAO))
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        extra = (" Os pontos medidos dela também são apagados."
                 if item.tipo == Tipo.CALIBRACAO else "")
        coluna = QVBoxLayout(self)
        coluna.addWidget(QLabel(f"<b>{item.tipo}: {item.descricao}</b>"))
        coluna.addWidget(QLabel("Isto apaga o item para sempre: não dá para desfazer nem "
                                f"restaurar.{extra} Para confirmar, digite "
                                f"<b>{CONFIRMACAO_EXCLUSAO}</b>.", wordWrap=True))
        coluna.addWidget(self.confirmacao)
        coluna.addWidget(botoes)
        self.setMinimumWidth(620)


class AbaLixeira(QWidget):
    alterado = Signal()  # algo voltou ou saiu de vez: a janela atualiza tudo

    def __init__(self, repositorio: Repositorio) -> None:
        super().__init__()
        self.repo = repositorio
        self.itens: list[ItemLixeira] = []

        self.filtro = QComboBox()
        self.filtro.addItems(FILTROS)
        self.filtro.currentTextChanged.connect(self._preencher)
        self.contagem = QLabel(objectName="dica")
        topo = QHBoxLayout()
        topo.addWidget(QLabel("Mostrar:"))
        topo.addWidget(self.filtro)
        topo.addWidget(QLabel("Use a Lixeira para o que foi registrado por engano. Restaurar "
                              "devolve o item para onde estava.", objectName="dica"), 1)
        topo.addWidget(self.contagem)

        self.tabela = tabela_somente_leitura(["Tipo", "Item", "Enviado em", "Motivo"])
        self.tabela.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabela.itemSelectionChanged.connect(self._habilitar)
        self.avisos = QLabel(wordWrap=True, objectName="avisos")

        self.restaurar = QPushButton("Restaurar")
        self.restaurar.clicked.connect(self.restaurar_item)
        self.excluir = QPushButton("Excluir permanentemente…")
        self.excluir.setToolTip(f"Apaga para sempre (pede para digitar {CONFIRMACAO_EXCLUSAO}).")
        self.excluir.clicked.connect(self.excluir_item)
        botoes = QHBoxLayout()
        botoes.addWidget(self.avisos, 2)
        botoes.addWidget(self.restaurar, 1)
        botoes.addWidget(self.excluir, 1)

        coluna = QVBoxLayout(self)
        coluna.addLayout(topo)
        coluna.addWidget(self.tabela, 1)
        coluna.addLayout(botoes)
        self._habilitar()

    def atualizar(self) -> None:
        self.itens = self.repo.listar_lixeira()
        self._preencher()

    def _visiveis(self) -> list[ItemLixeira]:
        tipo = FILTROS[self.filtro.currentText()]
        return [item for item in self.itens if tipo is None or item.tipo == tipo]

    def _preencher(self) -> None:
        visiveis = self._visiveis()
        self.tabela.setRowCount(len(visiveis))
        for linha, item in enumerate(visiveis):
            valores = [celula(item.tipo.value), celula(item.descricao),
                       celula(quando(item.excluido_em)), celula(item.motivo or "—")]
            valores[0].setData(Qt.UserRole, linha)
            for coluna, valor in enumerate(valores):
                self.tabela.setItem(linha, coluna, valor)
        self.contagem.setText(f"{len(visiveis)} item(ns)")
        self._habilitar()

    def selecionado(self) -> ItemLixeira | None:
        linhas = self.tabela.selectionModel().selectedRows()
        return self._visiveis()[linhas[0].row()] if linhas else None

    def _habilitar(self) -> None:
        tem = self.selecionado() is not None
        self.restaurar.setEnabled(tem)
        self.excluir.setEnabled(tem)

    # --- Ações ------------------------------------------------------------------------------

    def restaurar_item(self) -> None:
        item = self.selecionado()
        if item is None:
            return
        try:
            self.repo.restaurar(item.tipo, item.id)
        except ErroDeValidacao as erro:
            self._aviso("\n".join(f"✖ {m}" for m in erro.mensagens), erro=True)
            return
        self.alterado.emit()
        self._aviso(f"✔ Restaurado: {item.descricao}.")

    def excluir_item(self) -> None:
        item = self.selecionado()
        if item is None:
            return
        janela = JanelaExcluir(item, parent=self)
        if janela.exec():
            self.excluir_de_vez(item, janela.confirmacao.text())

    def excluir_de_vez(self, item: ItemLixeira, confirmacao: str) -> None:
        try:
            self.repo.excluir_permanentemente(item.tipo, item.id, confirmacao)
        except ErroDeValidacao as erro:
            self._aviso("\n".join(f"✖ {m}" for m in erro.mensagens), erro=True)
            return
        self.alterado.emit()
        self._aviso(f"✔ Excluído para sempre: {item.descricao}.")

    def _aviso(self, texto: str, erro: bool = False) -> None:
        self.avisos.setStyleSheet(f"color: {CORES['erro'] if erro else CORES['certo']};")
        self.avisos.setText(texto)
