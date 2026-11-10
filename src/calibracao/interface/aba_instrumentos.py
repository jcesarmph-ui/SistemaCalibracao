"""Aba Instrumentos: lista com filtros e busca à esquerda; dados do instrumento escolhido à direita.

Os dados são só apresentação (pedido do usuário em 2026-11-03): para mudar, EDITAR abre a janela
de edição no meio da tela (`janela_instrumento.py`). Mudar a condição e enviar para a Lixeira
abrem uma janelinha, para pedir data, observação e confirmação.
"""

import datetime
import html

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDateEdit,
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from calibracao.dados.repositorio import (
    ErroDeValidacao,
    Instrumento,
    MudancaCondicao,
    Repositorio,
)
from calibracao.interface.componentes import (
    aplicar_destaques,
    celula,
    data_livre_para_tela,
    dinheiro,
    formatar_data,
    tabela_somente_leitura,
)
from calibracao.interface.estilo import CORES_CONDICAO, destacar, tem_destaque
from calibracao.interface.janela_instrumento import JanelaEditarInstrumento
from calibracao.interface.lista_instrumentos import ListaInstrumentos
from calibracao.interface.painel_plano import ResumoPlano
from calibracao.regras.condicao import Condicao
from calibracao.regras.lixeira import Tipo

# O que acontece com o instrumento em cada condição (texto da janelinha de mudar condição).
EXPLICACAO_CONDICAO = {
    Condicao.EM_USO: "O instrumento volta a ser usado normalmente e segue no cronograma.",
    Condicao.DESATIVADO: "O instrumento sai do cronograma. O histórico de calibrações continua "
                         "guardado e ele pode voltar a ser usado depois.",
}


# Dados mostrados na ficha (só apresentação), em duas colunas: (chave, rótulo).
DADOS = [("codigo", "Código"), ("tipo", "Tipo de instrumento"), ("localizacao", "Localização"),
         ("faixa", "Faixa de utilização"), ("resolucao", "Resolução"), ("fabricante", "Fabricante"),
         ("data_compra", "Data de compra"), ("periodicidade_meses", "Periodicidade"),
         ("custo_compra", "Custo de compra"), ("responsavel", "Responsável"),
         ("primeira_prevista", "1ª calibração prevista"), ("plano", "Plano"),
         ("exige_calibracao", "Precisa de calibração"), ("condicao", "Condição"),
         ("observacoes", "Observações")]


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
        self.atual: Instrumento | None = None
        self.pode_editar = True
        self.janela_edicao: JanelaEditarInstrumento | None = None

        # Só o resumo do plano; VER PLANO e EDITAR PLANO abrem janelas grandes (item 12).
        self.painel_plano = ResumoPlano(repositorio)
        self.painel_plano.alterado.connect(self.alterado)
        self.painel_plano.alterado.connect(self.recarregar_atual)
        self.painel_plano.plano_descartado.connect(self.recarregar_atual)
        self.tabela_historico = tabela_somente_leitura(
            ["Data", "Condição", "Observação", "Origem"])
        self.subabas = QTabWidget()
        self.subabas.addTab(self.painel_plano, "Plano de calibração")
        # As calibrações ficam na aba Calibrar (pedido de 2026-11-03).
        self.subabas.addTab(self.tabela_historico, "Histórico de condição")

        self.lista = ListaInstrumentos()
        self.lista.escolhido.connect(
            lambda instrumento_id: self.mostrar(self.repo.obter_instrumento(instrumento_id)))
        # atalhos (usados pela janela e pelos testes)
        self.tabela, self.busca, self.contagem = (self.lista.tabela, self.lista.busca,
                                                  self.lista.contagem)
        self.filtro_condicao, self.filtro_tipo, self.filtro_local = (
            self.lista.filtro_condicao, self.lista.filtro_tipo, self.lista.filtro_local)

        direita = QVBoxLayout()
        direita.setContentsMargins(0, 0, 0, 0)
        direita.addWidget(self._caixa_dados())
        direita.addWidget(self.subabas, 1)
        coluna_direita = QWidget()
        coluna_direita.setLayout(direita)

        faixa = QHBoxLayout(self)
        faixa.addWidget(self.lista, 1)
        faixa.addWidget(coluna_direita, 1)
        self.mostrar(None)

    # --- Montagem ---------------------------------------------------------------------------

    def _caixa_dados(self) -> QGroupBox:
        """Só apresentação: rótulo e valor em duas colunas (para mudar, EDITAR)."""
        self.valores = {nome: QLabel(textFormat=Qt.RichText, wordWrap=True)
                        for nome, _ in DADOS}
        grade = QGridLayout()
        for indice, (nome, rotulo) in enumerate(DADOS):
            linha, coluna = divmod(indice, 2)
            grade.addWidget(QLabel(f"{rotulo}:"), linha, coluna * 2)
            grade.addWidget(self.valores[nome], linha, coluna * 2 + 1)
        grade.setColumnStretch(1, 1)
        grade.setColumnStretch(3, 1)

        self.editar = QPushButton("EDITAR", objectName="principal")
        self.editar.setToolTip("Abre a janela para mudar os dados deste instrumento.")
        self.editar.clicked.connect(self.editar_instrumento)
        self.novo = QPushButton("Novo instrumento")
        self.novo.clicked.connect(self.novo_instrumento)
        self.mudar_condicao = QPushButton("Mudar condição")
        self.mudar_condicao.setToolTip("Desativar ou voltar a usar, com data e observação.")
        self.mudar_condicao.clicked.connect(self.mudar_condicao_instrumento)
        self.lixeira = QPushButton("Enviar para a Lixeira")
        self.lixeira.clicked.connect(self.enviar_para_lixeira)
        botoes = QHBoxLayout()
        botoes.addWidget(self.novo, 1)
        botoes.addWidget(self.mudar_condicao, 1)
        botoes.addWidget(self.lixeira, 1)
        botoes.addWidget(self.editar, 2)

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
        self.lista.atualizar(self.repo.listar_instrumentos(incluir_desativados=True),
                             self.repo.condicoes_atuais(), situacoes)

    def mostrar(self, instrumento: Instrumento | None) -> None:
        self.atual = instrumento
        self.lista.marcar(instrumento.id if instrumento else None)
        if instrumento is None:
            for valor in self.valores.values():
                valor.setText("—")
            self.titulo_dados.setText("Escolha um instrumento na lista (clique no código).")
        else:
            self._mostrar_dados(instrumento)
            self.titulo_dados.setText(
                "Só para ver. Para mudar, clique em EDITAR." if self.pode_editar
                else f"Consultando {instrumento.codigo}")
        for botao in (self.editar, self.mudar_condicao, self.lixeira):
            botao.setEnabled(instrumento is not None)
        self.painel_plano.mostrar(instrumento.plano_id if instrumento else None)
        self._mostrar_condicao(instrumento)
        self._aviso("")

    def _mostrar_dados(self, instrumento: Instrumento) -> None:
        plano = "sem plano"
        if instrumento.plano_id is not None:
            plano = self.repo.obter_plano(instrumento.plano_id).nome
            if self.repo.na_lixeira(Tipo.PLANO, instrumento.plano_id):
                plano += " (na Lixeira)"
        atual = self.repo.condicao_atual(instrumento.id)
        desde = f" desde {formatar_data(atual.data)}" if atual.data else ""
        local = instrumento.localizacao or "—"
        textos = {
            "codigo": instrumento.codigo, "tipo": instrumento.tipo,
            "faixa": instrumento.faixa, "resolucao": instrumento.resolucao,
            "fabricante": instrumento.fabricante,
            "data_compra": data_livre_para_tela(instrumento.data_compra),
            "periodicidade_meses": (f"{instrumento.periodicidade_meses} meses"
                                    if instrumento.periodicidade_meses else None),
            "custo_compra": (dinheiro(instrumento.custo_compra)
                             if instrumento.custo_compra is not None else None),
            "responsavel": instrumento.responsavel,
            "primeira_prevista": (formatar_data(instrumento.primeira_prevista)
                                  if instrumento.primeira_prevista else None),
            "plano": plano,
            "exige_calibracao": "Sim" if instrumento.exige_calibracao else "Não",
            "condicao": f"{atual.condicao}{desde}",
            "observacoes": instrumento.observacoes,
        }
        for nome, texto in textos.items():
            self.valores[nome].setText(f"<b>{html.escape(texto)}</b>" if texto else "—")
        self.valores["localizacao"].setText(
            f"<b>{destacar(local) if tem_destaque(local) else html.escape(local)}</b>")

    def _mostrar_condicao(self, instrumento: Instrumento | None) -> None:
        historico = self.repo.historico_condicao(instrumento.id) if instrumento else []
        # Condição e marca de orientação indicativa juntas, por data (mais recente em cima).
        linhas = [(m.data, 0, n, m.condicao.value, CORES_CONDICAO[m.condicao], m.motivo,
                   "Parecer final da calibração" if m.calibracao_id else "Mudança manual")
                  for n, m in enumerate(historico)]
        marcas = self.repo.historico_indicativa(instrumento.id) if instrumento else []
        linhas += [(m.data, 1, n, "Orientação indicativa" if m.marcada
                    else "Deixou de ser orientação indicativa", None, m.motivo,
                    "Parecer final da calibração" if m.calibracao_id
                    else "Ficha do instrumento") for n, m in enumerate(marcas)]
        linhas.sort(key=lambda x: (x[0] or datetime.date.min, x[1], x[2]), reverse=True)
        tabela = self.tabela_historico
        tabela.setRowCount(len(linhas))
        for linha, (data, _, _, texto, cor, motivo, origem) in enumerate(linhas):
            itens = [celula(formatar_data(data)), celula(texto, cor), celula(motivo or "—"),
                     celula(origem)]
            for coluna, item in enumerate(itens):
                tabela.setItem(linha, coluna, item)
        aplicar_destaques(tabela)

    # --- Ações ------------------------------------------------------------------------------

    def definir_edicao(self, pode: bool) -> None:
        """Modo consulta: botões de mudar somem (os dados já são só apresentação)."""
        for botao in (self.novo, self.editar, self.mudar_condicao, self.lixeira):
            botao.setVisible(pode)
        self.pode_editar = pode
        self.painel_plano.definir_edicao(pode)
        if self.janela_edicao is not None and not pode:
            self.janela_edicao.reject()  # perdeu a edição: a janela de editar fecha
        self.recarregar_atual()

    def tem_alteracao(self) -> bool:
        """Algo digitado (na janela de edição ou no plano) e ainda não salvo."""
        return self.painel_plano.tem_alteracao() or (
            self.janela_edicao is not None and self.janela_edicao.tem_alteracao())

    def criar_janela_edicao(self, instrumento: Instrumento | None) -> JanelaEditarInstrumento:
        """A janela de editar (ou de novo instrumento), já ligada à aba; quem chama dá exec()."""
        janela = JanelaEditarInstrumento(self.repo, self.hoje, instrumento, parent=self)
        janela.salvo.connect(self._salvou)
        janela.finished.connect(self._fechou_edicao)
        self.janela_edicao = janela
        return janela

    def _fechou_edicao(self, _resultado: int) -> None:
        self.janela_edicao = None

    def editar_instrumento(self) -> None:
        if self.atual is not None:
            self.criar_janela_edicao(self.atual).exec()

    def novo_instrumento(self) -> None:
        self.criar_janela_edicao(None).exec()

    def _salvou(self, instrumento_id: int) -> None:
        instrumento = self.repo.obter_instrumento(instrumento_id)
        self.alterado.emit()
        self.mostrar(instrumento)
        self._aviso(f"✔ {instrumento.codigo} salvo.", certo=True)

    def recarregar_atual(self) -> None:
        """Redesenha o instrumento aberto (mudou algo pela Lixeira)."""
        if self.atual is None:
            return
        if self.repo.na_lixeira(Tipo.INSTRUMENTO, self.atual.id):
            self.mostrar(None)
        else:
            self.mostrar(self.repo.obter_instrumento(self.atual.id))

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
