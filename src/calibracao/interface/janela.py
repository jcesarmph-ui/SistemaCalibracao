"""Janela principal: cabeçalho, faixa de indicadores e abas de trabalho.

Layout em faixas (padrão MG): cabeçalho; indicadores (caixas iguais); abas Instrumentos,
Cronograma e Lixeira. Desativados não têm aba: aparecem na lista de instrumentos (filtro Condição).
Tudo o que é dado vem do `Repositorio`.

Uso em rede (ver `calibracao.regras.trava`): com `identidade` (usuário do Windows e nome do PC),
a janela pega a trava de edição ao abrir; se outra pessoa já estiver editando, abre em modo
consulta — faixa amarela no topo, botões de mudar escondidos e dados se atualizando sozinhos.
"""

import datetime
from pathlib import Path

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QComboBox,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPushButton,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

from calibracao import __version__
from calibracao.dados.repositorio import ErroDeValidacao, LinhaCronograma, Repositorio, Trava
from calibracao.interface.aba_instrumentos import AbaInstrumentos
from calibracao.interface.aba_lixeira import AbaLixeira
from calibracao.interface.componentes import (
    ListaFlutuante,
    PainelClicavel,
    aplicar_destaques,
    celula,
    formatar_data,
    tabela_somente_leitura,
)
from calibracao.interface.estilo import (
    CORES,
    CORES_PARECER,
    CORES_SITUACAO,
    estilo,
)
from calibracao.regras.cronograma import Situacao, somar_meses
from calibracao.regras.trava import INTERVALO_SINAL, ObservadorDeSinal

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

# Painéis que abrem a lista flutuante ao clicar (pedido do usuário em 2026-10-29): situações
# mostradas em cada um.
LISTAS_DOS_PAINEIS = {
    "vencidas": (Situacao.VENCIDA,),
    "mes": (Situacao.PENDENTE_MES, Situacao.FEITA_MES),
    "proximo_mes": (Situacao.PROXIMO_MES,),
}


class JanelaPrincipal(QMainWindow):
    def __init__(self, repositorio: Repositorio, pasta_dados: Path,
                 hoje: datetime.date | None = None,
                 identidade: tuple[str, str] | None = None) -> None:
        super().__init__()
        self.repo = repositorio
        self.pasta_dados = pasta_dados
        self.hoje = hoje or datetime.date.today()
        self.valores_indicadores: dict[str, QLabel] = {}

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
        tela.addWidget(self._faixa_consulta())
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
        if identidade is not None:
            self.tentar_editar()
            self.relogio.start()

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

    def _faixa_consulta(self) -> QWidget:
        """Faixa amarela do modo consulta (escondida enquanto esta janela pode editar)."""
        self.texto_consulta = QLabel(wordWrap=True, objectName="faixa_texto")
        self.passar_para_edicao = QPushButton("Passar para edição")
        self.passar_para_edicao.setToolTip("Funciona quando ninguém mais estiver editando.")
        self.passar_para_edicao.clicked.connect(self.pedir_edicao)
        self.faixa_consulta = QWidget(objectName="faixa_consulta")
        linha = QHBoxLayout(self.faixa_consulta)
        linha.addWidget(self.texto_consulta, 1)
        linha.addWidget(self.passar_para_edicao)
        self.faixa_consulta.setVisible(False)
        return self.faixa_consulta

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
                   "Situação", "Parecer da última"]
        self.tabela_cronograma = tabela_somente_leitura(colunas)

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
        self._preencher_cronograma(self.filtro_cronograma.currentText())
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
        except ErroDeValidacao as erro:  # banco ocupado: segue como estava
            self.texto_consulta.setText(f"✖ {erro.mensagens[0]}")
            return
        self.aplicar_modo(dono)

    def aplicar_modo(self, dono: Trava | None) -> None:
        """dono None = esta janela edita; senão, modo consulta mostrando quem edita."""
        pode = dono is None and not self.repo.modo_consulta
        for aba in (self.aba_instrumentos, self.aba_lixeira):
            aba.definir_edicao(pode)
        self.faixa_consulta.setVisible(not pode)
        self.setWindowTitle(self.titulo_janela if pode
                            else f"{self.titulo_janela} — SOMENTE CONSULTA")
        if not pode:
            self.observador.ver(dono.sinal if dono else None, self.agora())
            self._escrever_faixa(dono)

    def _escrever_faixa(self, dono: Trava | None) -> None:
        if dono is None:
            texto = ("SOMENTE CONSULTA — ninguém está editando agora: clique em "
                     "\"Passar para edição\".")
        elif self.observador.parado(self.agora()):
            texto = (f"SOMENTE CONSULTA — {dono.usuario} ({dono.computador}) parou de responder "
                     "(computador desligado ou travado): você pode passar para edição.")
        else:
            texto = (f"SOMENTE CONSULTA — {dono.usuario} ({dono.computador}) está editando "
                     f"desde {dono.desde:%H:%M}. Você vê tudo, mas não muda nada; os dados se "
                     "atualizam sozinhos a cada 30 segundos.")
        self.texto_consulta.setText(texto)

    def pedir_edicao(self) -> None:
        agora = self.agora()
        dono = self.repo.obter_trava()
        self.observador.ver(dono.sinal if dono else None, agora)
        assumir = self.observador.sinal if self.observador.parado(agora) else None
        self.tentar_editar(assumir)

    def a_cada_sinal(self) -> None:
        """A cada 30 s: quem edita avisa que continua; quem consulta relê os dados."""
        if not self.repo.modo_consulta:
            if not self.repo.dar_sinal(self.agora()):
                self.aplicar_modo(self.repo.obter_trava())
                self.texto_consulta.setText(
                    "SOMENTE CONSULTA — outra pessoa passou a editar enquanto este computador "
                    "ficou parado. O que não tinha sido salvo se perdeu.")
            return
        dono = self.repo.obter_trava()
        self.observador.ver(dono.sinal if dono else None, self.agora())
        self._escrever_faixa(dono)
        self.atualizar()
        self.aba_instrumentos.recarregar_atual()

    def closeEvent(self, evento) -> None:  # noqa: N802 — nome exigido pelo Qt
        self.relogio.stop()
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

    def _preencher_cronograma(self, filtro: str) -> None:
        linhas: list[LinhaCronograma] = [
            linha for linha in self._cronograma if filtro == "Todos" or linha.situacao == filtro
        ]
        tabela = self.tabela_cronograma
        tabela.setRowCount(len(linhas))
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
            ]
            for coluna, item in enumerate(valores):
                tabela.setItem(indice, coluna, item)
        aplicar_destaques(tabela)
        self.contagem_cronograma.setText(f"{len(linhas)} instrumento(s)")
