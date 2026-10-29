"""Aba Instrumentos: lista com busca à esquerda; dados do instrumento escolhido à direita.

Erros de digitação aparecem em vermelho na área de avisos (sem pop-up). Só desativar e enviar para
a Lixeira abrem uma janelinha, para pedir motivo e confirmação.
"""

import datetime

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QCheckBox,
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QVBoxLayout,
    QWidget,
)

from calibracao.dados.repositorio import ErroDeValidacao, Instrumento, Repositorio
from calibracao.interface.componentes import celula
from calibracao.interface.estilo import CORES_SITUACAO
from calibracao.regras.lixeira import Tipo


def _texto(campo: QLineEdit) -> str | None:
    return campo.text().strip() or None


class JanelaMotivo(QDialog):
    """Pede motivo (e, se for o caso, data) antes de desativar ou enviar para a Lixeira."""

    def __init__(self, titulo: str, explicacao: str, pedir_data: bool, motivo_obrigatorio: bool,
                 hoje: datetime.date, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.motivo = QLineEdit()
        self.data = QDateEdit(QDate(hoje.year, hoje.month, hoje.day), calendarPopup=True)
        self.data.setDisplayFormat("dd/MM/yyyy")
        self.data.setMaximumDate(QDate(hoje.year, hoje.month, hoje.day))
        formulario = QFormLayout()
        formulario.addRow(QLabel(explicacao, wordWrap=True))
        formulario.addRow("Motivo" + ("" if motivo_obrigatorio else " (opcional)"), self.motivo)
        if pedir_data:
            formulario.addRow("Data", self.data)
        self.aviso = QLabel(objectName="erro")
        formulario.addRow(self.aviso)
        botoes = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.button(QDialogButtonBox.Ok).setText("Confirmar")
        botoes.button(QDialogButtonBox.Cancel).setText("Cancelar")
        botoes.accepted.connect(self._confirmar if motivo_obrigatorio else self.accept)
        botoes.rejected.connect(self.reject)
        formulario.addRow(botoes)
        self.setLayout(formulario)
        self.setMinimumWidth(560)

    def _confirmar(self) -> None:
        if not self.motivo.text().strip():
            self.aviso.setText("✖ Informe o motivo.")
            return
        self.accept()

    def data_escolhida(self) -> datetime.date:
        return self.data.date().toPython()


class AbaInstrumentos(QWidget):
    alterado = Signal()  # algo mudou no banco: a janela atualiza indicadores e cronograma

    def __init__(self, repositorio: Repositorio, hoje: datetime.date) -> None:
        super().__init__()
        self.repo = repositorio
        self.hoje = hoje
        self.situacoes = {}  # id do instrumento → situação no cronograma
        self.atual: Instrumento | None = None

        faixa = QHBoxLayout(self)
        faixa.addWidget(self._caixa_lista(), 1)
        faixa.addWidget(self._caixa_dados(), 1)

    # --- Montagem ---------------------------------------------------------------------------

    def _caixa_lista(self) -> QGroupBox:
        self.busca = QLineEdit(placeholderText="Buscar por código, tipo ou localização")
        self.busca.textChanged.connect(self._preencher_lista)
        self.tabela = QTableWidget(0, 4)
        self.tabela.setHorizontalHeaderLabels(["Código", "Tipo", "Localização", "Situação"])
        self.tabela.verticalHeader().setVisible(False)
        self.tabela.setSelectionBehavior(QAbstractItemView.SelectRows)
        self.tabela.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabela.setEditTriggers(QAbstractItemView.NoEditTriggers)
        cabecalho = self.tabela.horizontalHeader()
        cabecalho.setSectionResizeMode(QHeaderView.Stretch)
        cabecalho.setSectionResizeMode(0, QHeaderView.ResizeToContents)
        self.tabela.itemSelectionChanged.connect(self._selecionou)
        self.contagem = QLabel(objectName="dica")

        caixa = QGroupBox("Instrumentos")
        coluna = QVBoxLayout(caixa)
        coluna.addWidget(self.busca)
        coluna.addWidget(self.tabela)
        coluna.addWidget(self.contagem)
        return caixa

    def _caixa_dados(self) -> QGroupBox:
        self.campos = {nome: QLineEdit() for nome in
                       ("codigo", "tipo", "localizacao", "faixa", "resolucao", "fabricante",
                        "data_compra", "periodicidade_meses")}
        self.campos["periodicidade_meses"].setToolTip("De quantos em quantos meses calibrar.")
        self.plano = QComboBox()
        self.exige = QCheckBox("Precisa de calibração")
        self.exige.setToolTip("Desmarque para instrumentos que não precisam de calibração: "
                              "eles saem do cronograma.")
        self.observacoes = QLineEdit()

        grade = QGridLayout()
        rotulos = [("codigo", "Código"), ("tipo", "Tipo"), ("localizacao", "Localização"),
                   ("faixa", "Faixa"), ("resolucao", "Resolução"), ("fabricante", "Fabricante"),
                   ("data_compra", "Data de compra"),
                   ("periodicidade_meses", "Periodicidade (meses)")]
        for indice, (nome, rotulo) in enumerate(rotulos):
            linha, coluna = divmod(indice, 2)
            grade.addWidget(QLabel(rotulo), linha, coluna * 2)
            grade.addWidget(self.campos[nome], linha, coluna * 2 + 1)
        grade.addWidget(QLabel("Plano"), 4, 0)
        grade.addWidget(self.plano, 4, 1, 1, 3)
        grade.addWidget(QLabel("Observações"), 5, 0)
        grade.addWidget(self.observacoes, 5, 1, 1, 3)
        grade.addWidget(self.exige, 6, 1, 1, 3)

        self.novo = QPushButton("Novo instrumento")
        self.novo.clicked.connect(self.novo_instrumento)
        self.salvar = QPushButton("SALVAR", objectName="principal")
        self.salvar.clicked.connect(self.salvar_instrumento)
        self.desativar = QPushButton("Desativar…")
        self.desativar.clicked.connect(self.desativar_instrumento)
        self.lixeira = QPushButton("Enviar para a Lixeira…")
        self.lixeira.clicked.connect(self.enviar_para_lixeira)
        botoes = QHBoxLayout()
        botoes.addWidget(self.novo, 1)
        botoes.addWidget(self.desativar, 1)
        botoes.addWidget(self.lixeira, 1)
        botoes.addWidget(self.salvar, 2)

        self.titulo_dados = QLabel(objectName="dica")
        self.avisos = QLabel(wordWrap=True, objectName="avisos")
        caixa = QGroupBox("Dados do instrumento")
        coluna = QVBoxLayout(caixa)
        coluna.addWidget(self.titulo_dados)
        coluna.addLayout(grade)
        coluna.addStretch()
        coluna.addWidget(self.avisos)
        coluna.addLayout(botoes)
        return caixa

    # --- Dados ------------------------------------------------------------------------------

    def atualizar(self, situacoes: dict) -> None:
        """Recarrega a lista (chamada pela janela, que já calculou o cronograma)."""
        self.situacoes = situacoes
        self._instrumentos = self.repo.listar_instrumentos()
        self.plano.clear()
        self.plano.addItem("— sem plano —", None)
        for plano in self.repo.listar_planos():
            self.plano.addItem(plano.nome, plano.id)
        self._preencher_lista(self.busca.text())

    def _preencher_lista(self, busca: str) -> None:
        termo = busca.strip().lower()
        visiveis = [i for i in self._instrumentos if not termo or termo in
                    f"{i.codigo} {i.tipo} {i.localizacao or ''}".lower()]
        selecionado = self.atual.id if self.atual else None
        self.tabela.blockSignals(True)
        self.tabela.setRowCount(len(visiveis))
        for linha, instrumento in enumerate(visiveis):
            situacao = self.situacoes.get(instrumento.id)
            itens = [celula(instrumento.codigo), celula(instrumento.tipo),
                     celula(instrumento.localizacao or "—"),
                     celula(situacao.value, CORES_SITUACAO[situacao]) if situacao
                     else celula("Não precisa de calibração")]
            itens[0].setData(Qt.UserRole, instrumento.id)
            for coluna, item in enumerate(itens):
                self.tabela.setItem(linha, coluna, item)
            if instrumento.id == selecionado:
                self.tabela.selectRow(linha)
        self.tabela.blockSignals(False)
        self.contagem.setText(f"{len(visiveis)} de {len(self._instrumentos)} instrumento(s)")

    def _selecionou(self) -> None:
        linhas = self.tabela.selectionModel().selectedRows()
        if not linhas:
            return
        instrumento_id = self.tabela.item(linhas[0].row(), 0).data(Qt.UserRole)
        self.mostrar(self.repo.obter_instrumento(instrumento_id))

    def mostrar(self, instrumento: Instrumento | None) -> None:
        self.atual = instrumento
        dados = instrumento or Instrumento(codigo="", tipo="")
        for nome, campo in self.campos.items():
            valor = getattr(dados, nome)
            campo.setText("" if valor is None else str(valor))
        self.plano.setCurrentIndex(max(self.plano.findData(dados.plano_id), 0))
        self.exige.setChecked(dados.exige_calibracao)
        self.observacoes.setText(dados.observacoes or "")
        self.titulo_dados.setText(f"Editando {dados.codigo}" if instrumento
                                  else "Novo instrumento: preencha e clique em SALVAR")
        self.desativar.setEnabled(instrumento is not None)
        self.lixeira.setEnabled(instrumento is not None)
        self._aviso("")

    # --- Ações ------------------------------------------------------------------------------

    def novo_instrumento(self) -> None:
        self.tabela.clearSelection()
        self.mostrar(None)
        self.campos["codigo"].setFocus()

    def salvar_instrumento(self) -> None:
        texto_meses = self.campos["periodicidade_meses"].text().strip()
        if texto_meses and not texto_meses.isdigit():
            self._aviso("✖ A periodicidade deve ser um número inteiro de meses.", erro=True)
            return
        instrumento = Instrumento(
            codigo=self.campos["codigo"].text().strip(),
            tipo=self.campos["tipo"].text().strip(),
            localizacao=_texto(self.campos["localizacao"]),
            faixa=_texto(self.campos["faixa"]),
            resolucao=_texto(self.campos["resolucao"]),
            fabricante=_texto(self.campos["fabricante"]),
            data_compra=_texto(self.campos["data_compra"]),
            periodicidade_meses=int(texto_meses) if texto_meses else None,
            plano_id=self.plano.currentData(),
            exige_calibracao=self.exige.isChecked(),
            observacoes=_texto(self.observacoes),
            id=self.atual.id if self.atual else None,
        )
        try:
            if instrumento.id is None:
                instrumento.id = self.repo.incluir_instrumento(instrumento)
            else:
                self.repo.atualizar_instrumento(instrumento)
        except ErroDeValidacao as erro:
            self._aviso("\n".join(f"✖ {m}" for m in erro.mensagens), erro=True)
            return
        self.atual = instrumento
        self.alterado.emit()
        self.mostrar(self.repo.obter_instrumento(instrumento.id))
        self._aviso(f"✔ {instrumento.codigo} salvo.", certo=True)

    def desativar_instrumento(self) -> None:
        if self.atual is None:
            return
        janela = JanelaMotivo(
            f"Desativar {self.atual.codigo}",
            "O instrumento sai da lista e do cronograma e vai para a aba Desativados. "
            "O histórico de calibrações continua guardado e ele pode ser reativado depois.",
            pedir_data=True, motivo_obrigatorio=True, hoje=self.hoje, parent=self)
        if not janela.exec():
            return
        try:
            self.repo.desativar_instrumento(self.atual.id, janela.data_escolhida(),
                                            janela.motivo.text(), self.hoje)
        except ErroDeValidacao as erro:
            self._aviso("\n".join(f"✖ {m}" for m in erro.mensagens), erro=True)
            return
        codigo = self.atual.codigo
        self.atual = None
        self.alterado.emit()
        self.mostrar(None)
        self._aviso(f"✔ {codigo} desativado.", certo=True)

    def enviar_para_lixeira(self) -> None:
        if self.atual is None:
            return
        janela = JanelaMotivo(
            f"Enviar {self.atual.codigo} para a Lixeira",
            "Use a Lixeira para o que foi cadastrado por engano. Para um instrumento que "
            "deixou de ser usado, prefira Desativar.",
            pedir_data=False, motivo_obrigatorio=False, hoje=self.hoje, parent=self)
        if not janela.exec():
            return
        codigo = self.atual.codigo
        self.repo.enviar_para_lixeira(Tipo.INSTRUMENTO, self.atual.id, janela.motivo.text(),
                                      datetime.datetime.now())
        self.atual = None
        self.alterado.emit()
        self.mostrar(None)
        self._aviso(f"✔ {codigo} enviado para a Lixeira.", certo=True)

    def _aviso(self, texto: str, erro: bool = False, certo: bool = False) -> None:
        cor = "#ef5350" if erro else "#43a047" if certo else "#ffd54f"
        self.avisos.setStyleSheet(f"color: {cor};")
        self.avisos.setText(texto)
