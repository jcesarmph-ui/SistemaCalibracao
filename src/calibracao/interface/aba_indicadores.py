"""Aba Indicadores (pedido de 2026-11-10): números de custo em cima e o painel de gráficos que o
próprio usuário monta (ADICIONAR GRÁFICO → montador com listas, sem IA). Um painel só para
todos (no banco); mexer só no modo edição. Lugar e tamanho fixos (2 por linha, na ordem em que
entraram). A setinha ↶ desfaz as 3 últimas mudanças nos gráficos (adicionar, editar, tirar).

O Matplotlib só é carregado quando a aba aparece (o programa abre rápido como antes).
"""

import datetime

from PySide6.QtCore import QSize, Qt, Signal
from PySide6.QtWidgets import (
    QComboBox,
    QDialog,
    QFormLayout,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QScrollArea,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from calibracao.dados.repositorio import ErroDeValidacao, Repositorio
from calibracao.interface.componentes import RotuloAviso, dinheiro
from calibracao.interface.estilo import CORES
from calibracao.interface.tema_icones import icone, por_icone
from calibracao.regras import indicadores as ind

MAXIMO_DESFAZER = 3   # só as 3 últimas mudanças nos gráficos (pedido de 2026-11-10)
ALTURA_DO_CARTAO = 430

EXEMPLOS = {
    "Calibrações por mês (no prazo × atraso)": ind.DefinicaoGrafico(
        ind.QTD_CALIBRACOES, ind.MES, ind.PRAZO),
    "Calibrações reprovadas por mês": ind.DefinicaoGrafico(
        ind.QTD_CALIBRACOES, ind.MES, filtros={ind.PARECER: "Reprovado - Desativado"}),
    "Custo por mês": ind.DefinicaoGrafico(ind.CUSTO, ind.MES),
    "Custo por laboratório": ind.DefinicaoGrafico(ind.CUSTO, ind.LABORATORIO,
                                                  forma=ind.DEITADAS),
    "Mais perto do limite": ind.DefinicaoGrafico(ind.PERTO_DO_LIMITE),
    "Instrumentos por tipo": ind.DefinicaoGrafico(ind.QTD_INSTRUMENTOS, ind.TIPO,
                                                  forma=ind.DEITADAS),
}


class JanelaGrafico(QDialog):
    """ADICIONAR GRÁFICO / Editar: perguntas simples à esquerda, o gráfico na hora à direita.
    Só oferece o que faz sentido; gráfico sem dados não pode ser adicionado."""

    def __init__(self, aba: "AbaIndicadores", definicao: ind.DefinicaoGrafico | None = None,
                 parent=None) -> None:
        super().__init__(parent)
        from calibracao.interface import desenho_grafico as desenho

        self.desenho = desenho
        self.aba = aba
        self.editando = definicao is not None
        self.setWindowTitle("Editar gráfico" if self.editando else "Adicionar gráfico")
        self.setWindowFlags(self.windowFlags() | Qt.WindowMaximizeButtonHint)
        self.setWindowState(Qt.WindowMaximized)
        self._montando = False
        self.titulo_mexido = self.editando

        exemplos = QGroupBox("Comece por um exemplo (ou monte do zero embaixo)")
        linha = QHBoxLayout(exemplos)
        for nome, exemplo in EXEMPLOS.items():
            botao = QPushButton(nome)
            botao.setCursor(Qt.PointingHandCursor)
            botao.clicked.connect(lambda _=False, e=exemplo: self.preencher(e, titulo=False))
            linha.addWidget(botao)

        self.medida = QComboBox()
        self.medida.addItems(ind.MEDIDAS)
        self.separar = QComboBox()
        self.cor = QComboBox()
        self.cor.addItems(ind.CORES_POR)
        opcoes = ind.opcoes_de_filtro(aba.calibracoes, aba.instrumentos)
        self.filtros: dict[str, QComboBox] = {}
        caixa_filtros = QWidget()
        grade = QGridLayout(caixa_filtros)
        grade.setContentsMargins(0, 0, 0, 0)
        for n, nome in enumerate(ind.FILTRAVEIS):
            combo = QComboBox()
            combo.addItems([ind.TODOS, *opcoes[nome]])
            self.filtros[nome] = combo
            grade.addWidget(QLabel(nome.split(" (")[0]), n // 2, (n % 2) * 2)
            grade.addWidget(combo, n // 2, (n % 2) * 2 + 1)
        self.periodo = QComboBox()
        self.periodo.addItems(ind.PERIODOS)
        self.forma = QComboBox()
        self.forma.addItems(ind.FORMAS)
        self.titulo = QLineEdit()
        self.titulo.textEdited.connect(lambda _: setattr(self, "titulo_mexido", True))
        perguntas = QGroupBox("Monte o gráfico")
        formulario = QFormLayout(perguntas)
        formulario.setVerticalSpacing(14)
        formulario.addRow(QLabel("<b>1. O que você quer ver?</b>"), self.medida)
        formulario.addRow(QLabel("<b>2. Separado por</b>"), self.separar)
        formulario.addRow(QLabel("<b>3. Só os que…</b> <i>(opcional)</i>"), caixa_filtros)
        formulario.addRow(QLabel("<b>4. Dividir a barra em cores?</b> <i>(opcional)</i>"),
                          self.cor)
        formulario.addRow(QLabel("<b>5. Período</b>"), self.periodo)
        formulario.addRow(QLabel("<b>6. Jeito do gráfico</b>"), self.forma)
        formulario.addRow(QLabel("<b>7. Título</b> <i>(escreve sozinho)</i>"), self.titulo)
        self.aviso = RotuloAviso(objectName="avisos", wordWrap=True)
        formulario.addRow(self.aviso)

        self.figura = desenho.nova_figura(7, 4.5)
        self.tela = desenho.TelaDoGrafico(self.figura)
        previa = QGroupBox("Assim vai ficar no painel (muda na hora)")
        QVBoxLayout(previa).addWidget(self.tela)
        meio = QHBoxLayout()
        meio.addWidget(perguntas, 2)
        meio.addWidget(previa, 3)

        self.ok = QPushButton("SALVAR GRÁFICO" if self.editando else "ADICIONAR AO PAINEL",
                              objectName="principal")
        self.ok.clicked.connect(self.accept)
        cancelar = QPushButton("Cancelar")
        cancelar.clicked.connect(self.reject)
        rodape = QHBoxLayout()
        rodape.addStretch(2)
        rodape.addWidget(cancelar, 1)
        rodape.addWidget(self.ok, 2)
        coluna = QVBoxLayout(self)
        coluna.addWidget(exemplos)
        coluna.addLayout(meio, 1)
        coluna.addLayout(rodape)

        for combo in [self.medida, self.separar, self.cor, self.periodo, self.forma,
                      *self.filtros.values()]:
            combo.currentIndexChanged.connect(self.atualizar)
        self.preencher(definicao or ind.DefinicaoGrafico(), titulo=self.editando)

    def preencher(self, definicao: ind.DefinicaoGrafico, titulo: bool) -> None:
        self._montando = True
        self.medida.setCurrentText(definicao.medida)
        self._acertar_separacoes()
        self.separar.setCurrentText(definicao.separar)
        self.cor.setCurrentText(definicao.cor)
        self.periodo.setCurrentText(definicao.periodo)
        self.forma.setCurrentText(definicao.forma)
        for nome, combo in self.filtros.items():
            combo.setCurrentText(definicao.filtros.get(nome, ind.TODOS))
        self.titulo_mexido = titulo
        self.titulo.setText(definicao.titulo)
        self._montando = False
        self.atualizar()

    def _acertar_separacoes(self) -> None:
        validas = ind.separacoes_validas(self.medida.currentText())
        if [self.separar.itemText(i) for i in range(self.separar.count())] != validas:
            atual = self.separar.currentText()
            self.separar.clear()
            self.separar.addItems(validas)
            self.separar.setCurrentText(atual if atual in validas else validas[0])

    def definicao(self) -> ind.DefinicaoGrafico:
        filtros = {nome: combo.currentText() for nome, combo in self.filtros.items()
                   if combo.isEnabled() and combo.currentText() != ind.TODOS}
        return ind.ajustar(ind.DefinicaoGrafico(
            self.medida.currentText(), self.separar.currentText(), self.cor.currentText(),
            filtros, self.periodo.currentText(), self.forma.currentText(),
            self.titulo.text().strip()))

    def atualizar(self) -> None:
        """Só deixa escolher o que faz sentido; redesenha a prévia; libera o botão se houver
        o que mostrar."""
        if self._montando:
            return
        self._montando = True
        medida = self.medida.currentText()
        self._acertar_separacoes()
        limite = medida == ind.PERTO_DO_LIMITE
        self.separar.setEnabled(not limite)
        self.forma.setEnabled(not limite)
        self.periodo.setEnabled(ind.usa_periodo(medida))
        if not ind.pode_dividir_em_cores(medida):
            self.cor.setCurrentIndex(0)
        self.cor.setEnabled(ind.pode_dividir_em_cores(medida))
        validos = ind.filtros_validos(medida)
        for nome, combo in self.filtros.items():
            if nome not in validos:
                combo.setCurrentIndex(0)
            combo.setEnabled(nome in validos)
        self._montando = False
        definicao = self.definicao()
        if not self.titulo_mexido:
            self.titulo.setText(ind.titulo_automatico(definicao))
            definicao.titulo = self.titulo.text()
        resultado = self.aba.calcular(definicao)
        self.desenho.desenhar(self.figura, definicao, resultado, estreito=True)
        self.tela.draw_idle()
        self.ok.setEnabled(not resultado.vazio)
        if resultado.vazio:
            self.ok.setToolTip("Este gráfico não mostra nada com essas escolhas: mude alguma "
                               "opção para poder adicionar.")
            self.aviso.setText(f"⚠ {resultado.aviso} Mude alguma opção para poder adicionar.")
        else:
            self.ok.setToolTip("")
            self.aviso.setText(
                "Mostra os 10 instrumentos cuja última calibração ficou mais perto do limite "
                "da tolerância (com a U). Acima de 100% = fora." if limite else "")


class CartaoGrafico(QGroupBox):
    """Um gráfico do painel: título na caixa, Editar e Tirar (só no modo edição)."""

    def __init__(self, aba: "AbaIndicadores", grafico_id: int,
                 definicao: ind.DefinicaoGrafico) -> None:
        super().__init__(definicao.titulo or ind.titulo_automatico(definicao))
        from calibracao.interface import desenho_grafico as desenho

        self.setFixedHeight(ALTURA_DO_CARTAO)
        self.editar = QPushButton("Editar")
        por_icone(self.editar, "edit", CORES["titulo"])
        self.editar.setToolTip("Mudar o que este gráfico mostra")
        self.editar.clicked.connect(lambda: aba.editar_grafico(grafico_id))
        self.tirar = QPushButton("Tirar")
        por_icone(self.tirar, "delete", CORES["titulo"])
        self.tirar.setToolTip("Tirar este gráfico do painel (sai também do relatório do mês)")
        self.tirar.clicked.connect(lambda: aba.tirar_grafico(grafico_id))
        for botao in (self.editar, self.tirar):
            botao.setVisible(aba.pode_editar)
        barra = QHBoxLayout()
        barra.addStretch(1)
        barra.addWidget(self.editar)
        barra.addWidget(self.tirar)
        figura = desenho.nova_figura()
        desenho.desenhar(figura, definicao, aba.calcular(definicao))
        coluna = QVBoxLayout(self)
        coluna.addLayout(barra)
        coluna.addWidget(desenho.TelaDoGrafico(figura), 1)


class AbaIndicadores(QWidget):
    alterado = Signal()

    def __init__(self, repositorio: Repositorio, hoje: datetime.date) -> None:
        super().__init__()
        self.repo = repositorio
        self.hoje = hoje
        self.pode_editar = True
        self.calibracoes: list[ind.CalibracaoParaIndicador] = []
        self.instrumentos: list[ind.InstrumentoParaIndicador] = []
        self.desfazer_lista: list[tuple[str, int, ind.DefinicaoGrafico | None]] = []
        self._precisa_desenhar = True

        self.numeros: dict[str, tuple[QLabel, QLabel]] = {}
        faixa = QHBoxLayout()
        for chave, titulo in [("mes", "Custo do mês"), ("doze", "Custo 12 meses"),
                              ("medio", "Custo médio por mês"), ("prazo", "No prazo")]:
            caixa = QGroupBox(titulo)
            valor = QLabel(objectName="indicador", alignment=Qt.AlignCenter)
            dica = QLabel(objectName="dica", alignment=Qt.AlignCenter)
            coluna = QVBoxLayout(caixa)
            coluna.addWidget(valor)
            coluna.addWidget(dica)
            self.numeros[chave] = (valor, dica)
            faixa.addWidget(caixa, 1)

        self.adicionar = QPushButton("  ADICIONAR GRÁFICO", objectName="principal")
        self.adicionar.setIcon(icone("add_chart", "#ffffff"))
        self.adicionar.setIconSize(QSize(28, 28))
        self.adicionar.setToolTip("Montar um gráfico novo e pôr no painel (ele entra também no "
                                  "relatório do mês)")
        self.adicionar.clicked.connect(self.novo_grafico)
        self.desfazer = QToolButton(objectName="botao_tema")  # mesma cara do botão sol/lua
        self.desfazer.setCursor(Qt.PointingHandCursor)
        self.desfazer.setIconSize(QSize(24, 24))
        self.desfazer.clicked.connect(self.desfazer_ultima)
        self.avisos = RotuloAviso(wordWrap=True, objectName="avisos")
        topo = QHBoxLayout()
        topo.addWidget(self.adicionar, 3)
        topo.addWidget(self.avisos, 4)
        topo.addWidget(self.desfazer)

        self.grade = QGridLayout()
        self.grade.setColumnStretch(0, 1)
        self.grade.setColumnStretch(1, 1)
        miolo = QWidget(objectName="central")
        coluna_miolo = QVBoxLayout(miolo)
        coluna_miolo.setContentsMargins(0, 0, 0, 0)
        coluna_miolo.addLayout(self.grade)
        coluna_miolo.addStretch(1)
        self.rolagem = QScrollArea(widgetResizable=True, objectName="rolagem_central")
        self.rolagem.setFrameShape(QScrollArea.NoFrame)
        self.rolagem.verticalScrollBar().setSingleStep(40)
        self.rolagem.setWidget(miolo)

        coluna = QVBoxLayout(self)
        coluna.addLayout(faixa)
        coluna.addLayout(topo)
        coluna.addWidget(self.rolagem, 1)
        self._pintar_desfazer()

    # --- dados ------------------------------------------------------------------------------
    def calcular(self, definicao: ind.DefinicaoGrafico) -> ind.ResultadoGrafico:
        return ind.calcular(definicao, self.calibracoes, self.instrumentos, self.hoje)

    def atualizar(self) -> None:
        """Relê o banco; os gráficos são redesenhados quando a aba estiver à vista."""
        self._precisa_desenhar = True
        if self.isVisible():
            self.redesenhar()

    def showEvent(self, evento) -> None:  # noqa: N802 — nome exigido pelo Qt
        super().showEvent(evento)
        if self._precisa_desenhar:
            self.redesenhar()

    def redesenhar(self) -> None:
        self._precisa_desenhar = False
        self.calibracoes, self.instrumentos = self.repo.dados_dos_indicadores()
        numeros = ind.numeros(self.calibracoes, self.hoje, self.repo.data_implantacao())
        mes = f"{ind.MESES_CURTOS[self.hoje.month - 1]}/{self.hoje.year}"
        valores = {
            "mes": (dinheiro(numeros.custo_do_mes), f"{mes} (até hoje)"),
            "doze": (dinheiro(numeros.custo_12_meses), "últimos 12 meses"),
            "medio": (dinheiro(numeros.custo_medio_mes), "por mês, nos 12 meses"),
            "prazo": (f"{numeros.no_prazo:.0f}%" if numeros.no_prazo is not None else "—",
                      f"das {numeros.feitas_12_meses} feitas nos 12 meses"),
        }
        for chave, (valor, dica) in valores.items():
            self.numeros[chave][0].setText(valor)
            self.numeros[chave][1].setText(dica)
        while self.grade.count():
            item = self.grade.takeAt(0)
            if item.widget():
                item.widget().deleteLater()
        graficos = self.repo.listar_graficos()
        for posicao, (grafico_id, definicao) in enumerate(graficos):
            self.grade.addWidget(CartaoGrafico(self, grafico_id, definicao),
                                 posicao // 2, posicao % 2)
        if not graficos:
            self.grade.addWidget(QLabel("O painel está vazio: clique em ADICIONAR GRÁFICO.",
                                        objectName="dica", alignment=Qt.AlignCenter),
                                 0, 0, 1, 2)

    # --- ações ------------------------------------------------------------------------------
    def novo_grafico(self) -> None:
        janela = JanelaGrafico(self, parent=self)
        if janela.exec():
            self.adicionar_definicao(janela.definicao())

    def adicionar_definicao(self, definicao: ind.DefinicaoGrafico) -> None:
        self._gravar(lambda: self.repo.incluir_grafico(definicao), "incluir",
                     "✔ Gráfico adicionado ao painel.")

    def editar_grafico(self, grafico_id: int) -> None:
        janela = JanelaGrafico(self, self.repo.obter_grafico(grafico_id), parent=self)
        if janela.exec():
            self.salvar_edicao(grafico_id, janela.definicao())

    def salvar_edicao(self, grafico_id: int, definicao: ind.DefinicaoGrafico) -> None:
        antes = self.repo.obter_grafico(grafico_id)
        self._gravar(lambda: self.repo.alterar_grafico(grafico_id, definicao) or grafico_id,
                     "editar", "✔ Gráfico alterado.", antes)

    def tirar_grafico(self, grafico_id: int) -> None:
        if self.confirmar_tirar(self.repo.obter_grafico(grafico_id).titulo):
            self._gravar(lambda: self.repo.tirar_grafico(grafico_id) or grafico_id, "tirar",
                         "✔ Gráfico tirado do painel.")

    def confirmar_tirar(self, titulo: str) -> bool:
        caixa = QMessageBox(self)
        caixa.setWindowTitle("Tirar gráfico")
        caixa.setText(f"Tirar \"{titulo}\" do painel?\n\nEle sai também do relatório do mês. "
                      "Dá para desfazer com a setinha ↶.")
        sim = caixa.addButton("Tirar", QMessageBox.AcceptRole)
        caixa.addButton("Cancelar", QMessageBox.RejectRole)
        caixa.exec()
        return caixa.clickedButton() is sim

    def _gravar(self, gravacao, tipo: str, mensagem: str,
                antes: ind.DefinicaoGrafico | None = None) -> None:
        try:
            grafico_id = gravacao()
        except ErroDeValidacao as erro:
            self._aviso("\n".join(f"✖ {m}" for m in erro.mensagens), erro=True)
            return
        self.desfazer_lista.append((tipo, grafico_id, antes))
        del self.desfazer_lista[:-MAXIMO_DESFAZER]
        self._pintar_desfazer()
        self.redesenhar()
        self._aviso(mensagem, certo=True)

    def desfazer_ultima(self) -> None:
        """Desfaz a última mudança nos gráficos (até 3 para trás)."""
        if not self.desfazer_lista:
            return
        tipo, grafico_id, antes = self.desfazer_lista[-1]
        try:
            if tipo == "incluir":
                self.repo.tirar_grafico(grafico_id)
            elif tipo == "editar":
                self.repo.alterar_grafico(grafico_id, antes)
            else:
                self.repo.voltar_grafico(grafico_id)
        except ErroDeValidacao as erro:
            self._aviso("\n".join(f"✖ {m}" for m in erro.mensagens), erro=True)
            return
        self.desfazer_lista.pop()
        self._pintar_desfazer()
        self.redesenhar()
        self._aviso({"incluir": "↶ Gráfico adicionado foi tirado.",
                     "editar": "↶ Gráfico voltou a ser como era.",
                     "tirar": "↶ Gráfico voltou para o painel."}[tipo], certo=True)

    def _pintar_desfazer(self) -> None:
        self.desfazer.setIcon(icone("undo", CORES["titulo"]))
        quantas = len(self.desfazer_lista)
        self.desfazer.setEnabled(bool(quantas))
        self.desfazer.setToolTip("Desfazer última alteração")  # texto pedido pelo usuário

    def definir_edicao(self, pode: bool) -> None:
        """Modo consulta: só ver os gráficos."""
        self.pode_editar = pode
        self.adicionar.setVisible(pode)
        self.desfazer.setVisible(pode)
        if not pode:
            self.desfazer_lista.clear()
        self._pintar_desfazer()
        self._precisa_desenhar = True
        if self.isVisible():
            self.redesenhar()

    def _aviso(self, texto: str, certo: bool = False, erro: bool = False) -> None:
        cor = CORES["erro"] if erro else CORES["certo"] if certo else CORES["aviso"]
        self.avisos.setStyleSheet(f"color: {cor};")
        self.avisos.setText(texto)
