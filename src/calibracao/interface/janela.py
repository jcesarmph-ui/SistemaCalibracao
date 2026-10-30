"""Janela principal: cabeçalho, faixa de indicadores e abas de trabalho.

Layout em faixas (padrão MG): cabeçalho; indicadores (caixas iguais); abas Instrumentos,
Cronograma e Lixeira. Desativados não têm aba: aparecem na lista de instrumentos (filtro Condição).
Tudo o que é dado vem do `Repositorio`.

Uso em rede (ver `calibracao.regras.trava`): com `identidade` (usuário do Windows e nome do PC),
a janela pega a trava de edição ao abrir; se outra pessoa já estiver editando, abre em modo
consulta — "Modo consulta - usuário - PC" no canto superior direito, botões de mudar
escondidos e dados se atualizando sozinhos; quando quem editava sai, passa sozinha para edição.

Com `copia_de` (o banco aberto é uma CÓPIA; ver `calibracao.dados.local_banco`), fica só em
consulta, com aviso amarelo; clicar no aviso e digitar MUDAR torna este o lugar oficial.
"""

import datetime
from pathlib import Path

from PySide6.QtCore import QEvent, Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QApplication,
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QInputDialog,
    QLabel,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from calibracao import __version__
from calibracao.dados.local_banco import local_do_banco
from calibracao.dados.repositorio import (
    ErroDeValidacao,
    LinhaCronograma,
    LinhaDoMes,
    Repositorio,
    Trava,
)
from calibracao.interface.aba_calibracoes import dinheiro
from calibracao.interface.aba_instrumentos import AbaInstrumentos
from calibracao.interface.aba_lixeira import AbaLixeira
from calibracao.interface.componentes import (
    ListaFlutuante,
    PainelClicavel,
    RotuloClicavel,
    aplicar_destaques,
    celula,
    formatar_data,
    tabela_somente_leitura,
)
from calibracao.interface.estilo import (
    CORES,
    CORES_PARECER,
    CORES_SITUACAO,
    CORES_SITUACAO_NO_MES,
    estilo,
)
from calibracao.interface.recursos import recurso
from calibracao.regras.cronograma import Situacao, SituacaoNoMes, meses_do_seletor, somar_meses
from calibracao.regras.trava import INTERVALO_SINAL, TEMPO_PARADO, ObservadorDeSinal

TITULO = "CALIBRAÇÃO DE INSTRUMENTOS"

# (texto do indicador, dica ao passar o mouse)
INDICADORES = {
    "instrumentos": ("Instrumentos", "Instrumentos ativos (fora da Lixeira e não desativados)."),
    "vencidas": ("Vencidas", "Previstas para um mês que já terminou e ainda não feitas."),
    "mes": ("CALIBRAÇÕES DE {mes}",
            "Previstas para este mês (dia 1 ao último dia): total | quantas ainda faltam fazer."),
    "proximo_mes": ("CALIBRAÇÕES DE {mes}", "Previstas para o mês que vem."),
}
# Acompanhamento por mês, como na MG (pedido do usuário em 2026-10-29). "Calibrações" e "Sem
# calibração no programa" não ficam no topo; o segundo aparece no filtro "Mostrar:" do Cronograma.

MESES = ["JANEIRO", "FEVEREIRO", "MARÇO", "ABRIL", "MAIO", "JUNHO", "JULHO", "AGOSTO",
         "SETEMBRO", "OUTUBRO", "NOVEMBRO", "DEZEMBRO"]

FILTROS_CRONOGRAMA = ["Todos", *[s.value for s in Situacao]]
HOJE_TODOS = "Hoje — todos os instrumentos"
COLUNAS_HOJE = ["Código", "Tipo", "Localização", "Última calibração", "Próxima calibração",
                "Situação", "Parecer da última", "Motivo do atraso"]
COLUNAS_MES = ["Código", "Tipo", "Localização", "Prevista", "Situação", "Feita em", "Custo",
               "Motivo do atraso"]

# Painéis que abrem a lista flutuante ao clicar (pedido do usuário em 2026-10-29): situações
# mostradas em cada um.
LISTAS_DOS_PAINEIS = {
    "vencidas": (Situacao.VENCIDA,),
    "mes": (Situacao.PENDENTE_MES, Situacao.FEITA_MES),
    "proximo_mes": (Situacao.PROXIMO_MES,),
}


def _localizacao_inteira(tabela) -> None:
    """Localização (3ª coluna) na largura do texto: "Orientação indicativa" não pode ser cortada."""
    tabela.horizontalHeader().setSectionResizeMode(2, QHeaderView.ResizeToContents)


def celula_motivo(motivo: str | None):
    """Motivo do atraso; o texto inteiro aparece ao passar o mouse (a coluna corta)."""
    item = celula(motivo or "")
    item.setToolTip(motivo or "")
    return item


class JanelaPrincipal(QMainWindow):
    def __init__(self, repositorio: Repositorio, pasta_dados: Path,
                 hoje: datetime.date | None = None,
                 identidade: tuple[str, str] | None = None,
                 copia_de: str | None = None) -> None:
        super().__init__()
        self.repo = repositorio
        self.pasta_dados = pasta_dados
        self.hoje = hoje or datetime.date.today()
        self.valores_indicadores: dict[str, QLabel] = {}
        self._pode_editar = True
        self._linhas_cronograma: list = []

        self.titulo_janela = (
            f"Calibração de Instrumentos — MG Centro de Serviços — versão {__version__}")
        self.setWindowTitle(self.titulo_janela)
        self.setStyleSheet(estilo())

        self.abas = QTabWidget()
        self.aba_instrumentos = AbaInstrumentos(repositorio, self.hoje)
        self.aba_instrumentos.alterado.connect(self.atualizar)
        self.abas.addTab(self.aba_instrumentos, "Instrumentos")
        self.abas.addTab(self._aba_cronograma(), "Cronograma")
        self.aba_lixeira = AbaLixeira(repositorio)
        self.aba_lixeira.alterado.connect(self._lixeira_mudou)
        self.abas.addTab(self.aba_lixeira, "Lixeira")
        self.abas.setCurrentIndex(1)

        tela = QVBoxLayout()
        tela.addLayout(self._cabecalho())
        self.aviso_copia = RotuloClicavel(objectName="aviso_copia", wordWrap=True)
        self.aviso_copia.setStyleSheet(f"background: {CORES['aviso']}; color: #000000; "
                                       "padding: 6px; font-weight: bold;")
        self.aviso_copia.setCursor(Qt.PointingHandCursor)
        self.aviso_copia.clicado.connect(self.mudar_pasta_oficial)
        self.aviso_copia.hide()
        tela.addWidget(self.aviso_copia)
        tela.addLayout(self._faixa_indicadores())
        tela.addWidget(self.abas, 1)
        central = QWidget(objectName="central")
        central.setLayout(tela)
        self.setCentralWidget(central)

        self.atualizar()

        # Trava de edição (só quando a janela sabe quem está usando: no programa de verdade).
        self.identidade = identidade
        self.observador = ObservadorDeSinal()
        self.relogio = QTimer(self)
        self.relogio.setInterval(int(INTERVALO_SINAL.total_seconds() * 1000))
        self.relogio.timeout.connect(self.a_cada_sinal)
        # Pedido de edição: conferido a cada 5 s, para a resposta não demorar.
        self.relogio_pedido = QTimer(self)
        self.relogio_pedido.setInterval(5000)
        self.relogio_pedido.timeout.connect(self.verificar_pedido)
        self.pedido_enviado = False
        self.situacao_pedido = ""          # " - pedido enviado" / " - pedido recusado"
        self.caixa_pedido: QMessageBox | None = None
        self._pedido_mostrado = None
        self.ultima_atividade = self.agora()
        self.liberou_parado_em: datetime.datetime | None = None
        self.copia_de = copia_de
        if identidade is not None:
            # quem corrige uma calibração fica registrado como "usuário - PC"
            self.aba_instrumentos.painel_calibracoes.usuario = " - ".join(identidade)
        if copia_de is not None:
            # Cópia: a trava daqui não vale para ninguém, então nunca edita.
            self.repo.modo_consulta = True
            self.aplicar_modo(None)
            pasta = Path(copia_de).parent.parent
            self.aviso_copia.setText(
                f"⚠ Esta é uma CÓPIA do banco: o oficial fica em {pasta}. Aqui é só consulta "
                "e os dados podem estar desatualizados. Se a pasta oficial do programa mudou "
                "para cá, clique aqui.")
            self.aviso_copia.show()
        elif identidade is not None:
            self._ligar_trava()

    def _ligar_trava(self) -> None:
        self.tentar_editar()
        self.relogio.start()
        self.relogio_pedido.start()
        QApplication.instance().installEventFilter(self)  # mouse/teclado = não está parado

    # --- Montagem da tela -------------------------------------------------------------------

    def _cabecalho(self) -> QGridLayout:
        """Logo à esquerda, título centralizado; à direita, o modo (em cima) e a versão."""
        arquivo_logo = recurso("logo_mg.png", self.pasta_dados)
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
        # "Modo edição" ou "Modo consulta - usuário - PC": pequeno, branco, discreto.
        self.rotulo_modo = RotuloClicavel("Modo edição", objectName="modo")
        self.rotulo_modo.clicado.connect(self.pedir_edicao)
        grade.addWidget(self.rotulo_modo, 0, 2, Qt.AlignRight | Qt.AlignTop)
        grade.setColumnStretch(0, 1)
        grade.setColumnStretch(2, 1)  # coluna do mesmo tamanho da do logo → título no centro
        return grade

    def _faixa_indicadores(self) -> QHBoxLayout:
        proximo = somar_meses(self.hoje.replace(day=1), 1)
        nomes_mes = {"mes": MESES[self.hoje.month - 1], "proximo_mes": MESES[proximo.month - 1]}
        faixa = QHBoxLayout()
        self.titulos_paineis = {}
        for chave, (texto, dica) in INDICADORES.items():
            titulo = texto.format(mes=nomes_mes.get(chave, ""))
            self.titulos_paineis[chave] = titulo
            if chave in LISTAS_DOS_PAINEIS:
                caixa = PainelClicavel(titulo)
                caixa.setToolTip(f"{dica} Clique para ver quais instrumentos são.")
                caixa.clicado.connect(lambda c=chave, p=caixa: self.mostrar_lista_do_painel(c, p))
            else:
                caixa = QGroupBox(titulo)
                caixa.setToolTip(dica)
            valor = QLabel("0", objectName="indicador", alignment=Qt.AlignCenter)
            QVBoxLayout(caixa).addWidget(valor)
            self.valores_indicadores[chave] = valor
            faixa.addWidget(caixa, 1)
        return faixa

    def _aba_cronograma(self) -> QWidget:
        """Hoje (todos os instrumentos, com a situação) ou um mês de 12 para trás a 24 para a
        frente: o que estava previsto, o que foi feito e o custo estimado."""
        self.mes_cronograma = QComboBox()
        self.mes_cronograma.setToolTip("Escolha um mês para ver o que está previsto nele (meses "
                                       "futuros repetem a periodicidade de cada instrumento).")
        self.mes_cronograma.addItem(HOJE_TODOS, None)
        for mes in meses_do_seletor(self.hoje):
            self.mes_cronograma.addItem(f"{MESES[mes.month - 1]}/{mes.year}", mes)
        self.mes_cronograma.currentIndexChanged.connect(lambda _: self._preencher_cronograma())
        self.filtro_cronograma = QComboBox()
        self.filtro_cronograma.addItems(FILTROS_CRONOGRAMA)
        self.filtro_cronograma.currentTextChanged.connect(lambda _: self._preencher_cronograma())
        self.rotulo_filtro = QLabel("Mostrar:")
        self.informar_motivo = QPushButton("Informar motivo do atraso")
        self.informar_motivo.setToolTip("Para calibração vencida: por que ainda não foi feita. "
                                        "Ao registrar a calibração, o motivo já vem preenchido.")
        self.informar_motivo.clicked.connect(self.pedir_motivo_atraso)
        topo = QHBoxLayout()
        topo.addWidget(QLabel("Mês:"))
        topo.addWidget(self.mes_cronograma)
        topo.addWidget(self.rotulo_filtro)
        topo.addWidget(self.filtro_cronograma)
        topo.addWidget(self.informar_motivo)
        topo.addStretch()
        self.contagem_cronograma = QLabel(objectName="dica")
        topo.addWidget(self.contagem_cronograma)

        self.tabela_cronograma = tabela_somente_leitura(COLUNAS_HOJE)
        self.tabela_cronograma.itemSelectionChanged.connect(self._ligar_informar_motivo)

        aba = QWidget()
        caixa = QVBoxLayout(aba)
        caixa.addLayout(topo)
        caixa.addWidget(self.tabela_cronograma)
        return aba

    # --- Dados ------------------------------------------------------------------------------

    def atualizar(self) -> None:
        """Relê o banco e redesenha indicadores e tabelas."""
        self._cronograma = self.repo.cronograma(self.hoje)
        contagem = {s: 0 for s in Situacao}
        for linha in self._cronograma:
            contagem[linha.situacao] += 1
        vencidas = contagem[Situacao.VENCIDA]
        pendentes = contagem[Situacao.PENDENTE_MES]
        total_mes = pendentes + contagem[Situacao.FEITA_MES]
        cor_vencidas = CORES["erro"] if vencidas else "#f0f0f0"
        cor_pendentes = CORES["aviso"] if pendentes else "#9e9e9e"
        textos = {
            "instrumentos": str(len(self.repo.listar_instrumentos())),
            "vencidas": f'<span style="color:{cor_vencidas}">{vencidas}</span>',
            "mes": f'{total_mes} <span style="color:#9e9e9e">|</span> '
                   f'<span style="color:{cor_pendentes}">{pendentes} '
                   f'pendente{"s" if pendentes != 1 else ""}</span>',
            "proximo_mes": str(contagem[Situacao.PROXIMO_MES]),
        }
        for chave, texto in textos.items():
            self.valores_indicadores[chave].setText(texto)
        self._preencher_cronograma()
        self.aba_instrumentos.atualizar(
            {linha.instrumento.id: linha.situacao for linha in self._cronograma})
        self.aba_lixeira.atualizar()

    # --- Trava de edição ---------------------------------------------------------------------

    @staticmethod
    def agora() -> datetime.datetime:
        return datetime.datetime.now()

    def tentar_editar(self, assumir_sinal: int | None = None) -> None:
        usuario, computador = self.identidade
        try:
            dono = self.repo.tentar_editar(usuario, computador, self.agora(), assumir_sinal)
        except ErroDeValidacao:  # banco ocupado: segue como estava e tenta no próximo sinal
            return
        self.aplicar_modo(dono)

    def aplicar_modo(self, dono: Trava | None) -> None:
        """dono None = esta janela edita; senão, modo consulta mostrando quem edita."""
        pode = dono is None and not self.repo.modo_consulta
        for aba in (self.aba_instrumentos, self.aba_lixeira):
            aba.definir_edicao(pode)
        self._pode_editar = pode
        self._ligar_informar_motivo()
        self.setWindowTitle(self.titulo_janela if pode
                            else f"{self.titulo_janela} — SOMENTE CONSULTA")
        if pode:
            self.pedido_enviado, self.situacao_pedido = False, ""
            self.rotulo_modo.setText("Modo edição")
            self.rotulo_modo.setCursor(Qt.ArrowCursor)
            self.rotulo_modo.setToolTip("")
            return
        self.observador.ver(dono.sinal if dono else None, self.agora())
        if self.copia_de is not None:
            self.rotulo_modo.setText("Modo consulta - cópia do banco")
            self.rotulo_modo.setCursor(Qt.ArrowCursor)
            self.rotulo_modo.setToolTip("Este banco é uma cópia: veja o aviso amarelo.")
            return
        texto = f"Modo consulta - {dono.usuario} - {dono.computador}" if dono else "Modo consulta"
        self.rotulo_modo.setText(texto + self.situacao_pedido)
        self.rotulo_modo.setCursor(Qt.PointingHandCursor)
        self.rotulo_modo.setToolTip("Outra pessoa está editando; aqui só se vê. Clique para pedir "
                                    "que ela libere a edição.")

    # --- Cópia do banco ----------------------------------------------------------------------

    def mudar_pasta_oficial(self) -> None:
        texto, ok = QInputDialog.getText(
            self, "A pasta oficial mudou para cá?",
            "Só confirme se o programa foi MOVIDO para esta pasta e todos vão abrir daqui.\n"
            "Se esta é só uma cópia, cancele: o que for gravado aqui não vai para o oficial.\n\n"
            "Digite MUDAR para confirmar:")
        if ok and not self.confirmar_pasta_oficial(texto):
            QMessageBox.warning(self, "Não mudou", "Nada foi mudado: era preciso digitar MUDAR.")

    def confirmar_pasta_oficial(self, texto: str) -> bool:
        """Com MUDAR digitado, este lugar vira o oficial e o programa volta ao normal."""
        if texto.strip().upper() != "MUDAR":
            return False
        self.repo.marcar_pasta_oficial(local_do_banco(self.pasta_dados / "calibracao.db"))
        self.copia_de = None
        self.aviso_copia.hide()
        self.repo.modo_consulta = False
        if self.identidade is not None:
            self._ligar_trava()
        else:
            self.aplicar_modo(None)
        return True

    # --- Pedido de edição ------------------------------------------------------------------

    def pedir_edicao(self) -> None:
        """Clique no texto do modo consulta: pede para quem edita liberar."""
        if not self.repo.modo_consulta or self.identidade is None or self.copia_de is not None:
            return
        usuario, computador = self.identidade
        try:
            enviado = self.repo.pedir_edicao(usuario, computador, self.agora())
        except ErroDeValidacao:
            return
        if not enviado:  # ninguém editando: já passa para edição
            self.tentar_editar()
            return
        self.pedido_enviado, self.situacao_pedido = True, " - pedido enviado"
        self.aplicar_modo(self.repo.obter_trava())

    def verificar_pedido(self) -> None:
        """A cada 5 s. Quem edita: mostra o pedido. Quem pediu: vê se foi liberado ou recusado."""
        trava = self.repo.obter_trava()
        if not self.repo.modo_consulta:
            if trava and trava.pedido_usuario:
                chave = (trava.pedido_usuario, trava.pedido_computador, trava.pedido_em)
                if chave != self._pedido_mostrado:
                    self._pedido_mostrado = chave
                    self._mostrar_pedido(trava)
            return
        if not self.pedido_enviado:
            return
        if trava is None:
            self.tentar_editar()  # liberou: passa para edição
        elif trava.pedido_usuario is None:
            self.pedido_enviado, self.situacao_pedido = False, " - pedido recusado"
            self.aplicar_modo(trava)

    def _mostrar_pedido(self, trava: Trava) -> None:
        texto = (f"{trava.pedido_usuario} ({trava.pedido_computador}) pediu para editar o "
                 "programa.\n\nSe liberar, este computador passa para o modo consulta.")
        if self.aba_instrumentos.tem_alteracao():
            texto += "\n\nAtenção: há alterações digitadas e não salvas. Salve antes de liberar."
        caixa = QMessageBox(QMessageBox.Question, "Pedido para editar", texto, parent=self)
        liberar = caixa.addButton("Liberar agora", QMessageBox.AcceptRole)
        caixa.addButton("Continuar editando", QMessageBox.RejectRole)
        caixa.setModal(False)  # não trava o programa de quem está editando
        caixa.buttonClicked.connect(lambda botao: self.responder_pedido(botao is liberar))
        self.caixa_pedido = caixa
        caixa.show()

    def responder_pedido(self, liberar: bool) -> None:
        if self.caixa_pedido is not None:
            self.caixa_pedido.close()
            self.caixa_pedido = None
        if self.repo.modo_consulta:
            return  # já tinha liberado (ex.: 30 minutos parado)
        if liberar:
            self.repo.liberar_trava()
            self.repo.modo_consulta = True
            self.liberou_parado_em = self.agora()  # não pega de volta sozinho
            self.aplicar_modo(None)
        else:
            self.repo.recusar_pedido()

    def eventFilter(self, objeto, evento) -> bool:  # noqa: N802 — nome exigido pelo Qt
        if evento.type() in (QEvent.MouseButtonPress, QEvent.KeyPress, QEvent.Wheel):
            self.ultima_atividade = self.agora()
        return super().eventFilter(objeto, evento)

    def _parado_sem_pendencia(self) -> bool:
        """30 minutos sem mouse nem teclado e nada digitado sem salvar."""
        if self.agora() - self.ultima_atividade < TEMPO_PARADO:
            return False
        janela_aberta = QApplication.activeModalWidget() is not None  # ex.: registrar calibração
        return not janela_aberta and not self.aba_instrumentos.tem_alteracao()

    def a_cada_sinal(self) -> None:
        """A cada 30 s: quem edita avisa que continua; quem consulta relê os dados e passa
        sozinho para edição quando ninguém mais estiver editando (pedido de 2026-10-29: sem
        faixa nem botão, só o texto do modo no canto)."""
        agora = self.agora()
        if not self.repo.modo_consulta:
            if self._parado_sem_pendencia():
                self.repo.liberar_trava()
                self.repo.modo_consulta = True
                self.liberou_parado_em = agora
                if self.caixa_pedido is not None:  # o pedido fica atendido
                    self.caixa_pedido.close()
                    self.caixa_pedido = None
                self.aplicar_modo(None)
            elif not self.repo.dar_sinal(agora):
                self.aplicar_modo(self.repo.obter_trava())  # outro assumiu: vira consulta
            return
        dono = self.repo.obter_trava()
        self.observador.ver(dono.sinal if dono else None, agora)
        # Quem liberou por estar parado só volta a editar depois de mexer no programa.
        voltou = self.liberou_parado_em is None or self.ultima_atividade > self.liberou_parado_em
        if voltou and (dono is None or self.observador.parado(agora)):
            self.tentar_editar(self.observador.sinal if dono else None)
        if self.repo.modo_consulta:
            self.aplicar_modo(self.repo.obter_trava())
        else:
            self.liberou_parado_em = None
        self.atualizar()
        self.aba_instrumentos.recarregar_atual()

    def closeEvent(self, evento) -> None:  # noqa: N802 — nome exigido pelo Qt
        self.relogio.stop()
        self.relogio_pedido.stop()
        if self.identidade is not None and not self.repo.modo_consulta:
            self.repo.liberar_trava()
        super().closeEvent(evento)

    def _lixeira_mudou(self) -> None:
        self.atualizar()
        self.aba_instrumentos.recarregar_atual()  # ex.: ponto restaurado volta ao plano aberto

    def mostrar_lista_do_painel(self, chave: str, painel: QWidget) -> None:
        """Janelinha com os instrumentos do painel (código, tipo, localização, situação)."""
        situacoes = LISTAS_DOS_PAINEIS[chave]
        linhas = sorted(
            (linha for linha in self._cronograma if linha.situacao in situacoes),
            key=lambda linha: (situacoes.index(linha.situacao), linha.proxima or self.hoje,
                               linha.instrumento.codigo),
        )
        itens = [
            [celula(linha.instrumento.codigo), celula(linha.instrumento.tipo),
             celula(linha.instrumento.localizacao or "—"),
             # feita: quando foi feita; as outras: quando está prevista
             celula(formatar_data(linha.ultima if linha.situacao == Situacao.FEITA_MES
                                  else linha.proxima)),
             celula(linha.situacao.value, CORES_SITUACAO[linha.situacao])]
            for linha in linhas
        ]
        self._lista_aberta = ListaFlutuante(
            self.titulos_paineis[chave],
            ["Código", "Tipo", "Localização", "Prevista / feita em", "Situação"], itens, self)
        self._lista_aberta.mostrar_abaixo_de(painel)

    def _preencher_cronograma(self) -> None:
        mes = self.mes_cronograma.currentData()
        self.rotulo_filtro.setVisible(mes is None)
        self.filtro_cronograma.setVisible(mes is None)
        if mes is None:
            self._preencher_hoje(self.filtro_cronograma.currentText())
        else:
            self._preencher_mes(self.repo.cronograma_do_mes(mes, self.hoje))
        self._ligar_informar_motivo()

    def _preencher_mes(self, linhas: list[LinhaDoMes]) -> None:
        tabela = self.tabela_cronograma
        tabela.setColumnCount(len(COLUNAS_MES))
        tabela.setHorizontalHeaderLabels(COLUNAS_MES)
        _localizacao_inteira(tabela)
        tabela.setRowCount(len(linhas))
        # (instrumento, é vencida em aberto?) de cada linha, para o botão do motivo do atraso
        self._linhas_cronograma = [
            (linha.instrumento, linha.prevista.situacao == SituacaoNoMes.VENCIDA)
            for linha in linhas]
        for indice, linha in enumerate(linhas):
            instrumento, prevista = linha.instrumento, linha.prevista
            valores = [
                celula(instrumento.codigo),
                celula(instrumento.tipo),
                celula(instrumento.localizacao or "—"),
                celula(formatar_data(prevista.prevista)),
                celula(prevista.situacao.value, CORES_SITUACAO_NO_MES[prevista.situacao]),
                celula(formatar_data(prevista.realizada) if prevista.realizada else "—"),
                celula(dinheiro(prevista.custo)),
                celula_motivo(prevista.motivo_atraso),
            ]
            for coluna, item in enumerate(valores):
                tabela.setItem(indice, coluna, item)
        aplicar_destaques(tabela)
        feitas = sum(1 for linha in linhas if linha.prevista.situacao == SituacaoNoMes.FEITA)
        custo = sum(linha.prevista.custo or 0.0 for linha in linhas)
        self.contagem_cronograma.setText(
            f"{len(linhas)} prevista(s) | {feitas} feita(s) | Custo estimado: {dinheiro(custo)}")

    def _preencher_hoje(self, filtro: str) -> None:
        linhas: list[LinhaCronograma] = [
            linha for linha in self._cronograma if filtro == "Todos" or linha.situacao == filtro
        ]
        tabela = self.tabela_cronograma
        tabela.setColumnCount(len(COLUNAS_HOJE))
        tabela.setHorizontalHeaderLabels(COLUNAS_HOJE)
        _localizacao_inteira(tabela)
        tabela.setRowCount(len(linhas))
        self._linhas_cronograma = [(linha.instrumento, linha.situacao == Situacao.VENCIDA)
                                   for linha in linhas]
        for indice, linha in enumerate(linhas):
            instrumento = linha.instrumento
            parecer = linha.parecer_ultima
            valores = [
                celula(instrumento.codigo),
                celula(instrumento.tipo),
                celula(instrumento.localizacao or "—"),
                celula(formatar_data(linha.ultima)),
                celula(formatar_data(linha.proxima)),
                celula(linha.situacao.value, CORES_SITUACAO[linha.situacao]),
                celula(parecer.value, CORES_PARECER[parecer]) if parecer else celula("—"),
                celula_motivo(linha.motivo_atraso),
            ]
            for coluna, item in enumerate(valores):
                tabela.setItem(indice, coluna, item)
        aplicar_destaques(tabela)
        self.contagem_cronograma.setText(f"{len(linhas)} instrumento(s)")

    # --- Motivo do atraso (vencidas) ----------------------------------------------------------

    def _vencida_escolhida(self):
        """O instrumento da linha escolhida, se ela for uma calibração vencida em aberto."""
        linhas = self.tabela_cronograma.selectionModel().selectedRows()
        if not linhas:
            return None
        instrumento, vencida = self._linhas_cronograma[linhas[0].row()]
        return instrumento if vencida else None

    def _ligar_informar_motivo(self) -> None:
        """O botão só aparece quando há vencida na lista (e quem usa pode editar)."""
        tem_vencida = any(vencida for _, vencida in self._linhas_cronograma)
        self.informar_motivo.setVisible(self._pode_editar and tem_vencida)
        self.informar_motivo.setEnabled(self._vencida_escolhida() is not None)

    def pedir_motivo_atraso(self) -> None:
        instrumento = self._vencida_escolhida()
        if instrumento is None:
            return
        atual = self.repo.motivos_atraso_pendentes().get(instrumento.id, "")
        motivo, ok = QInputDialog.getText(
            self, "Motivo do atraso",
            f"Por que a calibração de {instrumento.codigo} ainda não foi feita?\n"
            "(deixe vazio para apagar)", text=atual)
        if ok:
            self.informar_motivo_atraso(instrumento.id, motivo)

    def informar_motivo_atraso(self, instrumento_id: int, motivo: str) -> None:
        try:
            self.repo.informar_motivo_atraso(instrumento_id, motivo)
        except ErroDeValidacao as erro:
            QMessageBox.warning(self, "Não foi salvo", "\n".join(erro.mensagens))
            return
        self.atualizar()
