"""Aba Instrumentos: lista com filtros e busca à esquerda; dados do instrumento escolhido à direita.

Erros de digitação aparecem em vermelho na área de avisos (sem pop-up). Só mudar a condição e
enviar para a Lixeira abrem uma janelinha, para pedir data, observação e confirmação.
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
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from calibracao.dados.repositorio import (
    ErroDeValidacao,
    Instrumento,
    MudancaCondicao,
    Plano,
    Repositorio,
)
from calibracao.interface.aba_calibracoes import PainelCalibracoes
from calibracao.interface.componentes import (
    aplicar_destaques,
    celula,
    formatar_data,
    tabela_somente_leitura,
)
from calibracao.interface.estilo import CORES_CONDICAO, CORES_SITUACAO
from calibracao.interface.painel_plano import PainelPlano, numero, numero_em_texto
from calibracao.regras.condicao import Condicao
from calibracao.regras.lixeira import Tipo

# Filtro "Condição" da lista: condições mostradas em cada opção (pedido do usuário em 2026-10-29).
# A lista abre na primeira; os desativados só aparecem escolhendo o filtro.
FILTROS_CONDICAO = {
    "Todos menos desativados": (Condicao.EM_USO, Condicao.ORIENTACAO_INDICATIVA),
    "Em uso": (Condicao.EM_USO,),
    "Orientação indicativa": (Condicao.ORIENTACAO_INDICATIVA,),
    "Desativados": (Condicao.DESATIVADO,),
    "Todos": tuple(Condicao),
}
TODOS_OS_TIPOS = "Todos os tipos"
TODAS_AS_LOCALIZACOES = "Todas as localizações"

# O que acontece com o instrumento em cada condição (texto da janelinha de mudar condição).
EXPLICACAO_CONDICAO = {
    Condicao.EM_USO: "O instrumento volta a ser usado normalmente e segue no cronograma.",
    Condicao.ORIENTACAO_INDICATIVA: "O instrumento continua sendo usado só como orientação "
                                    "indicativa e segue no cronograma.",
    Condicao.DESATIVADO: "O instrumento sai do cronograma. O histórico de calibrações continua "
                         "guardado e ele pode voltar a ser usado depois.",
}


def _texto(campo: QLineEdit) -> str | None:
    return campo.text().strip() or None


def _data_qt(data: datetime.date) -> QDate:
    return QDate(data.year, data.month, data.day)


class JanelaMotivo(QDialog):
    """Pede motivo antes de enviar para a Lixeira."""

    def __init__(self, titulo: str, explicacao: str, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(titulo)
        self.motivo = QLineEdit()
        formulario = QFormLayout()
        formulario.addRow(QLabel(explicacao, wordWrap=True))
        formulario.addRow("Motivo (opcional)", self.motivo)
        botoes = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.button(QDialogButtonBox.Ok).setText("Confirmar")
        botoes.button(QDialogButtonBox.Cancel).setText("Cancelar")
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        formulario.addRow(botoes)
        self.setLayout(formulario)
        self.setMinimumWidth(560)


class JanelaCondicao(QDialog):
    """Mudar a condição: nova condição, data e observação opcional."""

    def __init__(self, codigo: str, atual: MudancaCondicao, hoje: datetime.date,
                 parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Mudar a condição de {codigo}")
        desde = f" desde {formatar_data(atual.data)}" if atual.data else ""
        self.condicao = QComboBox()
        for condicao in Condicao:
            if condicao != atual.condicao:
                self.condicao.addItem(condicao.value, condicao)
        self.explicacao = QLabel(wordWrap=True, objectName="dica")
        self.condicao.currentIndexChanged.connect(self._explicar)
        self.data = QDateEdit(_data_qt(hoje), calendarPopup=True)
        self.data.setDisplayFormat("dd/MM/yyyy")
        self.data.setMaximumDate(_data_qt(hoje))
        self.motivo = QLineEdit()
        formulario = QFormLayout()
        formulario.addRow(QLabel(f"Condição atual: <b>{atual.condicao}</b>{desde}"))
        formulario.addRow("Nova condição", self.condicao)
        formulario.addRow(self.explicacao)
        formulario.addRow("Data", self.data)
        formulario.addRow("Observação (opcional)", self.motivo)
        botoes = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        botoes.button(QDialogButtonBox.Ok).setText("Confirmar")
        botoes.button(QDialogButtonBox.Cancel).setText("Cancelar")
        botoes.accepted.connect(self.accept)
        botoes.rejected.connect(self.reject)
        formulario.addRow(botoes)
        self.setLayout(formulario)
        self.setMinimumWidth(620)
        self._explicar()

    def _explicar(self) -> None:
        self.explicacao.setText(EXPLICACAO_CONDICAO[self.condicao.currentData()])

    def condicao_escolhida(self) -> Condicao:
        return self.condicao.currentData()

    def data_escolhida(self) -> datetime.date:
        return self.data.date().toPython()


class AbaInstrumentos(QWidget):
    alterado = Signal()  # algo mudou no banco: a janela atualiza indicadores e cronograma

    def __init__(self, repositorio: Repositorio, hoje: datetime.date) -> None:
        super().__init__()
        self.repo = repositorio
        self.hoje = hoje
        self.situacoes = {}  # id do instrumento → situação no cronograma
        self.condicoes: dict[int, MudancaCondicao] = {}
        self._instrumentos: list[Instrumento] = []
        self.atual: Instrumento | None = None
        self.pode_editar = True

        self.painel_plano = PainelPlano(repositorio)
        self.painel_plano.alterado.connect(self.alterado)
        self.painel_plano.plano_descartado.connect(self.recarregar_atual)
        self.tabela_historico = tabela_somente_leitura(
            ["Data", "Condição", "Observação", "Origem"])
        self.subabas = QTabWidget()
        self.subabas.addTab(self.painel_plano, "Plano de calibração")
        self.painel_calibracoes = PainelCalibracoes(repositorio, hoje)
        self.painel_calibracoes.alterado.connect(self._calibracoes_mudaram)
        self.subabas.addTab(self.painel_calibracoes, "Calibrações")
        self.subabas.addTab(self.tabela_historico, "Histórico de condição")

        direita = QVBoxLayout()
        direita.setContentsMargins(0, 0, 0, 0)
        direita.addWidget(self._caixa_dados())
        direita.addWidget(self.subabas, 1)
        coluna_direita = QWidget()
        coluna_direita.setLayout(direita)

        faixa = QHBoxLayout(self)
        faixa.addWidget(self._caixa_lista(), 1)
        faixa.addWidget(coluna_direita, 1)

    # --- Montagem ---------------------------------------------------------------------------

    def _caixa_lista(self) -> QGroupBox:
        self.filtro_condicao = QComboBox()
        self.filtro_condicao.addItems(FILTROS_CONDICAO)
        self.filtro_condicao.setToolTip("Mostrar só os instrumentos nesta condição.")
        self.filtro_tipo = QComboBox()
        self.filtro_tipo.setToolTip("Ex.: escolha Paquímetro para ver todos os paquímetros.")
        self.filtro_local = QComboBox()
        for filtro in (self.filtro_condicao, self.filtro_tipo, self.filtro_local):
            filtro.currentTextChanged.connect(self._preencher_lista)
        self.busca = QLineEdit(placeholderText="Buscar por código, tipo ou localização")
        self.busca.textChanged.connect(self._preencher_lista)

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
        self.contagem = QLabel(objectName="dica")

        filtros = QHBoxLayout()
        filtros.addWidget(self.filtro_condicao, 1)
        filtros.addWidget(self.filtro_tipo, 1)
        filtros.addWidget(self.filtro_local, 1)
        caixa = QGroupBox("Instrumentos")
        coluna = QVBoxLayout(caixa)
        coluna.addLayout(filtros)
        coluna.addWidget(self.busca)
        coluna.addWidget(self.tabela)
        coluna.addWidget(self.contagem)
        return caixa

    def _caixa_dados(self) -> QGroupBox:
        self.campos = {nome: QLineEdit() for nome in
                       ("codigo", "tipo", "localizacao", "faixa", "resolucao", "fabricante",
                        "data_compra", "periodicidade_meses", "custo_compra", "responsavel")}
        self.campos["periodicidade_meses"].setToolTip("De quantos em quantos meses calibrar.")
        self.campos["custo_compra"].setToolTip("Valor pago na compra, em reais (ex.: 350,00).")
        self.plano = QComboBox()
        self.exige = QCheckBox("Precisa de calibração")
        self.exige.setToolTip("Desmarque para instrumentos que não precisam de calibração: "
                              "eles saem do cronograma.")
        self.observacoes = QLineEdit()

        grade = QGridLayout()
        rotulos = [("codigo", "Código"), ("tipo", "Tipo"), ("localizacao", "Localização"),
                   ("faixa", "Faixa"), ("resolucao", "Resolução"), ("fabricante", "Fabricante"),
                   ("data_compra", "Data de compra"),
                   ("periodicidade_meses", "Periodicidade (meses)"),
                   ("custo_compra", "Custo de compra (R$)"), ("responsavel", "Responsável")]
        for indice, (nome, rotulo) in enumerate(rotulos):
            linha, coluna = divmod(indice, 2)
            grade.addWidget(QLabel(rotulo), linha, coluna * 2)
            grade.addWidget(self.campos[nome], linha, coluna * 2 + 1)
        self.novo_plano = QPushButton("Novo plano")
        self.novo_plano.setToolTip("Cria um plano vazio; depois inclua os pontos na sub-aba "
                                   "Plano de calibração.")
        self.novo_plano.clicked.connect(self.pedir_nome_do_plano)
        grade.addWidget(QLabel("Plano"), 5, 0)
        grade.addWidget(self.plano, 5, 1, 1, 2)
        grade.addWidget(self.novo_plano, 5, 3)
        grade.addWidget(QLabel("Observações"), 6, 0)
        grade.addWidget(self.observacoes, 6, 1, 1, 3)
        grade.addWidget(self.exige, 7, 1)
        self.condicao_atual = QLabel()
        grade.addWidget(self.condicao_atual, 7, 2, 1, 2)

        self.novo = QPushButton("Novo instrumento")
        self.novo.clicked.connect(self.novo_instrumento)
        self.salvar = QPushButton("SALVAR", objectName="principal")
        self.salvar.clicked.connect(self.salvar_instrumento)
        self.mudar_condicao = QPushButton("Mudar condição")
        self.mudar_condicao.setToolTip("Desativar, voltar a usar ou marcar como orientação "
                                       "indicativa, com data e observação.")
        self.mudar_condicao.clicked.connect(self.mudar_condicao_instrumento)
        self.lixeira = QPushButton("Enviar para a Lixeira")
        self.lixeira.clicked.connect(self.enviar_para_lixeira)
        botoes = QHBoxLayout()
        botoes.addWidget(self.novo, 1)
        botoes.addWidget(self.mudar_condicao, 1)
        botoes.addWidget(self.lixeira, 1)
        botoes.addWidget(self.salvar, 2)

        self.titulo_dados = QLabel(objectName="dica")
        self.avisos = QLabel(wordWrap=True, objectName="avisos")
        caixa = QGroupBox("Dados do instrumento")
        coluna = QVBoxLayout(caixa)
        coluna.addWidget(self.titulo_dados)
        coluna.addLayout(grade)
        coluna.addWidget(self.avisos)
        coluna.addLayout(botoes)
        return caixa

    # --- Dados ------------------------------------------------------------------------------

    def atualizar(self, situacoes: dict) -> None:
        """Recarrega a lista (chamada pela janela, que já calculou o cronograma)."""
        self.situacoes = situacoes
        self.condicoes = self.repo.condicoes_atuais()
        self._instrumentos = self.repo.listar_instrumentos(incluir_desativados=True)
        self._recarregar_planos()
        self._recarregar_opcoes(self.filtro_tipo, TODOS_OS_TIPOS,
                                {i.tipo for i in self._instrumentos})
        self._recarregar_opcoes(self.filtro_local, TODAS_AS_LOCALIZACOES,
                                {i.localizacao for i in self._instrumentos if i.localizacao})
        self._preencher_lista()

    def _recarregar_planos(self) -> None:
        self.plano.clear()
        self.plano.addItem("— sem plano —", None)
        for plano in self.repo.listar_planos():
            self.plano.addItem(plano.nome, plano.id)

    @staticmethod
    def _recarregar_opcoes(filtro: QComboBox, todos: str, opcoes: set[str]) -> None:
        """Repõe as opções do filtro mantendo a escolha atual (se ela ainda existir)."""
        escolhido = filtro.currentText()
        filtro.blockSignals(True)
        filtro.clear()
        filtro.addItems([todos, *sorted(opcoes, key=str.lower)])
        filtro.setCurrentText(escolhido if escolhido in opcoes else todos)
        filtro.blockSignals(False)

    def _condicao(self, instrumento_id: int) -> MudancaCondicao:
        return self.condicoes.get(instrumento_id, MudancaCondicao(Condicao.EM_USO, None))

    def _visiveis(self) -> list[Instrumento]:
        termo = self.busca.text().strip().lower()
        condicoes = FILTROS_CONDICAO[self.filtro_condicao.currentText()]
        tipo = self.filtro_tipo.currentText()
        local = self.filtro_local.currentText()
        return [
            i for i in self._instrumentos
            if self._condicao(i.id).condicao in condicoes
            and tipo in (TODOS_OS_TIPOS, i.tipo)
            and local in (TODAS_AS_LOCALIZACOES, i.localizacao)
            and (not termo or termo in f"{i.codigo} {i.tipo} {i.localizacao or ''}".lower())
        ]

    def _preencher_lista(self) -> None:
        visiveis = self._visiveis()
        selecionado = self.atual.id if self.atual else None
        self.tabela.blockSignals(True)
        self.tabela.setRowCount(len(visiveis))
        for linha, instrumento in enumerate(visiveis):
            condicao = self._condicao(instrumento.id)
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
            itens[0].setToolTip(instrumento.tipo)
            for coluna, item in enumerate(itens):
                self.tabela.setItem(linha, coluna, item)
            if instrumento.id == selecionado:
                self.tabela.selectRow(linha)
        aplicar_destaques(self.tabela)
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
            if nome == "custo_compra":
                campo.setText(numero_em_texto(valor))
            else:
                campo.setText("" if valor is None else str(valor))
        if dados.plano_id is not None and self.plano.findData(dados.plano_id) < 0:
            # plano na Lixeira: continua aparecendo, para não sumir sem ninguém perceber
            nome = self.repo.obter_plano(dados.plano_id).nome
            self.plano.addItem(f"{nome} (na Lixeira)", dados.plano_id)
        self.plano.setCurrentIndex(max(self.plano.findData(dados.plano_id), 0))
        self.exige.setChecked(dados.exige_calibracao)
        self.observacoes.setText(dados.observacoes or "")
        if not self.pode_editar:
            self.titulo_dados.setText(f"Consultando {dados.codigo}" if instrumento else "")
        else:
            self.titulo_dados.setText(f"Editando {dados.codigo}" if instrumento
                                      else "Novo instrumento: preencha e clique em SALVAR")
        self.mudar_condicao.setEnabled(instrumento is not None)
        self.lixeira.setEnabled(instrumento is not None)
        self.painel_plano.mostrar(instrumento.plano_id if instrumento else None)
        self.painel_calibracoes.mostrar(instrumento)
        self._mostrar_condicao(instrumento)
        self._aviso("")

    def _mostrar_condicao(self, instrumento: Instrumento | None) -> None:
        historico = self.repo.historico_condicao(instrumento.id) if instrumento else []
        if instrumento is None:
            self.condicao_atual.setText("")
        else:
            atual = historico[-1] if historico else MudancaCondicao(Condicao.EM_USO, None)
            desde = f" desde {formatar_data(atual.data)}" if atual.data else ""
            self.condicao_atual.setText(f"Condição: <b>{atual.condicao}</b>{desde}")
        tabela = self.tabela_historico
        tabela.setRowCount(len(historico))
        for linha, mudanca in enumerate(reversed(historico)):  # mais recente em cima
            origem = "Parecer final da calibração" if mudanca.calibracao_id else "Mudança manual"
            itens = [celula(formatar_data(mudanca.data)),
                     celula(mudanca.condicao.value, CORES_CONDICAO[mudanca.condicao]),
                     celula(mudanca.motivo or "—"), celula(origem)]
            for coluna, item in enumerate(itens):
                tabela.setItem(linha, coluna, item)
        aplicar_destaques(tabela)

    # --- Ações ------------------------------------------------------------------------------

    def definir_edicao(self, pode: bool) -> None:
        """Modo consulta: botões de mudar somem e os campos não aceitam digitação."""
        for botao in (self.novo, self.salvar, self.mudar_condicao, self.lixeira):
            botao.setVisible(pode)
        for campo in (*self.campos.values(), self.observacoes):
            campo.setReadOnly(not pode)
        self.plano.setEnabled(pode)
        self.novo_plano.setVisible(pode)
        self.exige.setEnabled(pode)
        self.pode_editar = pode
        self.painel_plano.definir_edicao(pode)
        self.painel_calibracoes.definir_edicao(pode)
        self.recarregar_atual()

    def tem_alteracao(self) -> bool:
        """Algo digitado na ficha ou no plano e ainda não salvo."""
        if self.painel_plano.tem_alteracao():
            return True
        dados = self.atual or Instrumento(codigo="", tipo="")
        for nome, campo in self.campos.items():
            valor = getattr(dados, nome)
            salvo = (numero_em_texto(valor) if nome == "custo_compra"
                     else "" if valor is None else str(valor))
            if campo.text().strip() != salvo.strip():
                return True
        return ((self.observacoes.text().strip() != (dados.observacoes or "").strip())
                or (self.atual is not None and (self.plano.currentData() != dados.plano_id
                                                or self.exige.isChecked()
                                                != dados.exige_calibracao)))

    def pedir_nome_do_plano(self) -> None:
        from PySide6.QtWidgets import QInputDialog
        codigo = self.campos["codigo"].text().strip()
        nome, ok = QInputDialog.getText(self, "Novo plano", "Nome do plano:",
                                        text=f"Plano {codigo}" if codigo else "Plano ")
        if ok:
            self.criar_plano(nome)

    def criar_plano(self, nome: str) -> None:
        """Cria o plano e já o escolhe no campo Plano (falta clicar em SALVAR para ligar)."""
        try:
            plano_id = self.repo.incluir_plano(Plano(nome))
        except ErroDeValidacao as erro:
            self._aviso("\n".join(f"✖ {m}" for m in erro.mensagens), erro=True)
            return
        self._recarregar_planos()
        self.plano.setCurrentIndex(self.plano.findData(plano_id))
        self._aviso(f"Plano \"{nome.strip()}\" criado. Clique em SALVAR para ligá-lo a este "
                    "instrumento e depois inclua os pontos na sub-aba Plano de calibração.")

    def recarregar_atual(self) -> None:
        """Redesenha o instrumento aberto (mudou algo pela Lixeira)."""
        if self.atual is None:
            return
        if self.repo.na_lixeira(Tipo.INSTRUMENTO, self.atual.id):
            self.mostrar(None)
        else:
            self.mostrar(self.repo.obter_instrumento(self.atual.id))

    def _calibracoes_mudaram(self) -> None:
        """Calibração registrada ou na Lixeira: cronograma, condição e histórico mudam."""
        instrumento = self.atual
        self.alterado.emit()
        self.mostrar(self.repo.obter_instrumento(instrumento.id))

    def novo_instrumento(self) -> None:
        self.tabela.clearSelection()
        self.mostrar(None)
        self.campos["codigo"].setFocus()

    def salvar_instrumento(self) -> None:
        texto_meses = self.campos["periodicidade_meses"].text().strip()
        if texto_meses and not texto_meses.isdigit():
            self._aviso("✖ A periodicidade deve ser um número inteiro de meses.", erro=True)
            return
        try:
            custo = numero(self.campos["custo_compra"].text().replace("R$", ""))
        except ValueError:
            self._aviso("✖ O custo de compra deve ser um número (ex.: 350,00).", erro=True)
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
            custo_compra=custo,
            responsavel=_texto(self.campos["responsavel"]),
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

    def mudar_condicao_instrumento(self) -> None:
        if self.atual is None:
            return
        janela = JanelaCondicao(self.atual.codigo, self.repo.condicao_atual(self.atual.id),
                                self.hoje, parent=self)
        if not janela.exec():
            return
        self.aplicar_condicao(janela.condicao_escolhida(), janela.data_escolhida(),
                              janela.motivo.text())

    def aplicar_condicao(self, condicao: Condicao, data: datetime.date, motivo: str) -> None:
        try:
            self.repo.mudar_condicao(self.atual.id, condicao, data, motivo, self.hoje)
        except ErroDeValidacao as erro:
            self._aviso("\n".join(f"✖ {m}" for m in erro.mensagens), erro=True)
            return
        instrumento = self.atual
        self.alterado.emit()
        self.mostrar(self.repo.obter_instrumento(instrumento.id))
        self._aviso(f"✔ {instrumento.codigo}: condição mudada para \"{condicao}\".", certo=True)

    def enviar_para_lixeira(self) -> None:
        if self.atual is None:
            return
        janela = JanelaMotivo(
            f"Enviar {self.atual.codigo} para a Lixeira",
            "Use a Lixeira para o que foi cadastrado por engano. Para um instrumento que "
            "deixou de ser usado, prefira Mudar condição → Desativado.", parent=self)
        if not janela.exec():
            return
        codigo = self.atual.codigo
        try:
            self.repo.enviar_para_lixeira(Tipo.INSTRUMENTO, self.atual.id, janela.motivo.text(),
                                          datetime.datetime.now())
        except ErroDeValidacao as erro:
            self._aviso("\n".join(f"✖ {m}" for m in erro.mensagens), erro=True)
            return
        self.atual = None
        self.alterado.emit()
        self.mostrar(None)
        self._aviso(f"✔ {codigo} enviado para a Lixeira.", certo=True)

    def _aviso(self, texto: str, erro: bool = False, certo: bool = False) -> None:
        cor = "#ef5350" if erro else "#43a047" if certo else "#ffd54f"
        self.avisos.setStyleSheet(f"color: {cor};")
        self.avisos.setText(texto)
