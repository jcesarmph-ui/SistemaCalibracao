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

from PySide6.QtCore import QEvent, QSize, Qt, QTimer
from PySide6.QtGui import QColor, QImage, QPixmap
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
    QScrollArea,
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
from calibracao.interface.aba_calibrar import AbaCalibrar
from calibracao.interface.aba_certificados import AbaCertificados
from calibracao.interface.aba_instrumentos import AbaInstrumentos
from calibracao.interface.aba_lixeira import AbaLixeira
from calibracao.interface.componentes import (
    ListaFlutuante,
    PainelClicavel,
    RotuloAviso,
    RotuloClicavel,
    aplicar_destaques,
    celula,
    formatar_data,
    instalar_filtro_roda,
    preenchendo,
    tabela_somente_leitura,
)
from calibracao.interface.estilo import (
    CORES,
    CORES_PARECER,
    CORES_SITUACAO,
    CORES_SITUACAO_NO_MES,
    estilo,
    tema_claro,
)
from calibracao.interface.recursos import recurso
from calibracao.interface.tema_icones import icone, pixmap, por_icone
from calibracao.regras.cronograma import Situacao, SituacaoNoMes, meses_do_seletor, somar_meses
from calibracao.regras.trava import (
    INTERVALO_CONSULTA,
    INTERVALO_SINAL,
    TEMPO_PARADO,
    ObservadorDeSinal,
)

TITULO = "DQ-05 CALIBRAÇÃO DE INSTRUMENTOS"  # "DQ-05" pedido de 2026-11-10

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


INICIO_DAS_LETRAS = 0.32  # o símbolo ocupa o primeiro terço do logo; depois vêm as letras


def logo_com_letra_preta(imagem: QPixmap) -> QPixmap:
    """Tema claro: as letras brancas do logo viram pretas (o símbolo, à esquerda, não muda)."""
    figura = imagem.toImage().convertToFormat(QImage.Format_ARGB32)
    for x in range(int(figura.width() * INICIO_DAS_LETRAS), figura.width()):
        for y in range(figura.height()):
            cor = figura.pixelColor(x, y)
            if cor.alpha() and min(cor.red(), cor.green(), cor.blue()) > 150:
                figura.setPixelColor(x, y, QColor(0, 0, 0, cor.alpha()))
    return QPixmap.fromImage(figura)


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

        self.de_teste = repositorio.banco_de_teste()
        self.titulo_janela = (
            f"Calibração de Instrumentos — MG Centro de Serviços — versão {__version__}"
            + (" — TESTE" if self.de_teste else ""))
        self.setWindowTitle(self.titulo_janela)
        self.setStyleSheet(estilo())
        instalar_filtro_roda()  # a roda do mouse só rola, nunca muda nada

        self.abas = QTabWidget()
        self.aba_instrumentos = AbaInstrumentos(repositorio, self.hoje)
        self.aba_instrumentos.alterado.connect(self.atualizar)
        self.abas.addTab(self.aba_instrumentos, "Instrumentos")
        # Aba Calibrar (pedido de 2026-11-03): onde se faz a calibração.
        self.aba_calibrar = AbaCalibrar(repositorio, self.hoje)
        self.aba_calibrar.alterado.connect(self._calibracoes_mudaram)
        self.abas.addTab(self.aba_calibrar, "Calibrar")
        self.aba_cronograma = self._aba_cronograma()
        self.abas.addTab(self.aba_cronograma, "Cronograma")
        # Aba Certificados (pedido de 2026-11-10): os PDFs das calibrações feitas no programa.
        self.aba_certificados = AbaCertificados(repositorio)
        self.abas.addTab(self.aba_certificados, "Certificados")
        self.aba_lixeira = AbaLixeira(repositorio)
        self.aba_lixeira.alterado.connect(self._lixeira_mudou)
        self.abas.addTab(self.aba_lixeira, "Lixeira")
        # Ícones nas abas (aprovados por foto em 2026-11-10).
        for indice, nome in enumerate(["straighten", "tune", "event_note", "picture_as_pdf",
                                    "delete"]):
            self.abas.setTabIcon(indice, icone(nome, CORES["titulo"]))
        self.abas.setIconSize(QSize(22, 22))
        self.abas.setCurrentWidget(self.aba_cronograma)  # abre no Cronograma

        tela = QVBoxLayout()
        tela.addLayout(self._cabecalho())
        # Programa de TESTE: faixa amarela fina, para nunca confundir com o oficial.
        self.faixa_teste = QLabel(
            "VERSÃO DE TESTE — os dados daqui não valem: pode incluir, mudar e excluir à vontade",
            objectName="faixa_teste", alignment=Qt.AlignCenter)
        self.faixa_teste.setStyleSheet(f"background: {CORES['aviso_fundo']}; color: #000000; "
                                       "padding: 4px; font-weight: bold;")
        self.faixa_teste.setVisible(self.de_teste)
        tela.addWidget(self.faixa_teste)
        self.aviso_copia = RotuloClicavel(objectName="aviso_copia", wordWrap=True)
        self.aviso_copia.setStyleSheet(f"background: {CORES['aviso_fundo']}; color: #000000; "
                                       "padding: 6px; font-weight: bold;")
        self.aviso_copia.setCursor(Qt.PointingHandCursor)
        self.aviso_copia.clicado.connect(self.mudar_pasta_oficial)
        self.aviso_copia.hide()
        tela.addWidget(self.aviso_copia)
        tela.addLayout(self._faixa_indicadores())
        tela.addWidget(self.abas, 1)
        central = QWidget(objectName="central")
        central.setLayout(tela)
        # Proteção (achado no teste de 2026-11-03): se a tela não comporta tudo, aparece a barra
        # de rolagem dentro da janela, em vez de a parte de baixo ficar sob a barra do Windows.
        rolagem = QScrollArea(objectName="rolagem_central", widgetResizable=True)
        rolagem.setFrameShape(QScrollArea.NoFrame)
        rolagem.setWidget(central)
        self.setCentralWidget(rolagem)

        self.atualizar()

        # "✔ Salvo" por cima, no alto, a cada gravação que deu certo (item 3 do teste,
        # 2026-11-03); some sozinho.
        # O mesmo lugar mostra a resposta do pedido de edição (verde/vermelho, item 7) e o
        # "Atualizado" do botão Atualizar (item 8).
        self.aviso_salvo = RotuloAviso("✔ Salvo", self, cor_icone="#ffffff",
                                       objectName="aviso_salvo")
        self.aviso_salvo.hide()
        self.relogio_salvo = QTimer(self, singleShot=True, interval=3500)
        self.relogio_salvo.timeout.connect(self._apagar_aviso)
        self.repo.ao_gravar = self.mostrar_salvo

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
        self.situacao_pedido = ""          # "" / "enviado" / "aceito" / "recusado"
        self.caixa_pedido: QMessageBox | None = None
        self._pedido_mostrado = None
        self.ultima_atividade = self.agora()
        self.liberou_parado_em: datetime.datetime | None = None
        self.copia_de = copia_de
        if identidade is not None:
            # quem corrige uma calibração fica registrado como "usuário - PC"
            self.aba_calibrar.painel_calibracoes.usuario = " - ".join(identidade)
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
            imagem = QPixmap(str(arquivo_logo)).scaledToHeight(80, Qt.SmoothTransformation)
            logo.setPixmap(logo_com_letra_preta(imagem) if tema_claro() else imagem)
        else:
            logo = QLabel("MG Centro de Serviços")
        grade = QGridLayout()
        grade.addWidget(logo, 0, 0, Qt.AlignLeft)
        titulo = f"{TITULO} — TESTE" if self.de_teste else TITULO
        grade.addWidget(QLabel(titulo, objectName="titulo"), 0, 1)
        grade.addWidget(QLabel(f"versão {__version__}", objectName="dica"), 0, 2,
                        Qt.AlignRight | Qt.AlignBottom)
        # "Modo edição" ou "Modo consulta - usuário - PC": pequeno, branco, discreto. No modo
        # consulta, ao lado, os botões "Atualizar" e "Pedir edição" (itens 6 e 8 do teste).
        self.rotulo_modo = RotuloClicavel("Modo edição", objectName="modo")
        self.rotulo_modo.clicado.connect(self.pedir_edicao)
        self.botao_atualizar = QPushButton("Atualizar", objectName="canto")
        self.botao_atualizar.setToolTip("Mostra agora o que o outro computador mudou "
                                        "(sozinho, a tela se atualiza a cada 10 segundos).")
        self.botao_atualizar.clicked.connect(self.atualizar_agora)
        self.botao_pedir = QPushButton("Pedir edição", objectName="canto")
        self.botao_pedir.setToolTip("Pede para quem está editando liberar a edição para você.")
        self.botao_pedir.clicked.connect(self.pedir_edicao)
        por_icone(self.botao_atualizar, "refresh", CORES["titulo"])
        por_icone(self.botao_pedir, "back_hand", CORES["titulo"])
        # Cadeado aberto (edição) ou fechado (consulta) antes do texto do canto.
        self.cadeado = QLabel()
        self.cadeado.setPixmap(pixmap("lock_open", CORES["titulo"], 16))
        for botao in (self.botao_atualizar, self.botao_pedir):
            botao.setCursor(Qt.PointingHandCursor)
            botao.hide()
        canto = QHBoxLayout()
        canto.setSpacing(8)
        canto.addWidget(self.botao_atualizar)
        canto.addWidget(self.botao_pedir)
        canto.addWidget(self.cadeado)
        canto.addWidget(self.rotulo_modo)
        grade.addLayout(canto, 0, 2, Qt.AlignRight | Qt.AlignTop)
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
        """Hoje (todos os instrumentos, com a situação) ou um mês — o atual e 24 para a frente;
        embaixo, os que já passaram desde a implantação: o que estava previsto, o que foi feito
        e o custo estimado."""
        self.mes_cronograma = QComboBox()
        self.mes_cronograma.setToolTip("Escolha um mês para ver o que está previsto nele (meses "
                                       "futuros repetem a periodicidade de cada instrumento).")
        self.mes_cronograma.addItem(HOJE_TODOS, None)
        for mes in meses_do_seletor(self.hoje, self.repo.data_implantacao()):
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
        cor_vencidas = CORES["erro"] if vencidas else CORES["texto"]
        cor_pendentes = CORES["aviso"] if pendentes else CORES["dica"]
        textos = {
            "instrumentos": str(len(self.repo.listar_instrumentos())),
            "vencidas": f'<span style="color:{cor_vencidas}">{vencidas}</span>',
            "mes": f'{total_mes} <span style="color:{CORES["dica"]}">|</span> '
                   f'<span style="color:{cor_pendentes}">{pendentes} '
                   f'pendente{"s" if pendentes != 1 else ""}</span>',
            "proximo_mes": str(contagem[Situacao.PROXIMO_MES]),
        }
        for chave, texto in textos.items():
            self.valores_indicadores[chave].setText(texto)
        self._preencher_cronograma()
        situacoes = {linha.instrumento.id: linha.situacao for linha in self._cronograma}
        self.aba_instrumentos.atualizar(situacoes)
        self.aba_calibrar.atualizar(situacoes)
        self.aba_certificados.atualizar()
        self.aba_lixeira.atualizar()

    # --- Trava de edição ---------------------------------------------------------------------

    def mostrar_salvo(self) -> None:
        self.mostrar_aviso("✔ Salvo", CORES["dentro"], CORES["certo"])

    def mostrar_aviso(self, texto: str, fundo: str, borda: str, ms: int = 3500) -> None:
        self.aviso_salvo.setText(texto)
        self.aviso_salvo.setStyleSheet(f"background: {fundo}; color: #ffffff; "
                                       "font-size: 16pt; font-weight: bold; padding: 8px 40px; "
                                       f"border: 2px solid {borda}; border-radius: 6px;")
        self.relogio_salvo.setInterval(ms)
        self.aviso_salvo.adjustSize()
        # Na linha das abas, à direita (espaço vazio: não cobre nada).
        barra = self.abas.tabBar()
        canto = barra.mapTo(self, barra.rect().topLeft())
        self.aviso_salvo.move(self.width() - self.aviso_salvo.width() - 24,
                              canto.y() + (barra.height() - self.aviso_salvo.height()) // 2)
        self.aviso_salvo.show()
        self.aviso_salvo.raise_()
        self.relogio_salvo.stop()
        # Conta os 3,5 s só depois que a tela terminar de se atualizar (a gravação vem antes).
        QTimer.singleShot(0, self.relogio_salvo.start)

    def _apagar_aviso(self) -> None:
        self.aviso_salvo.hide()
        if self.situacao_pedido == "aceito":  # o contorno verde do canto some junto
            self.situacao_pedido = ""
            self._contorno_do_modo()

    def _contorno_do_modo(self) -> None:
        """Contorno do texto do canto: amarelo = pedido esperando resposta; verde = aceito;
        vermelho = recusado (item 7 do teste)."""
        cor = {"enviado": CORES["aviso"], "aceito": CORES["certo"],
               "recusado": CORES["botao"]}.get(self.situacao_pedido)
        self.rotulo_modo.setStyleSheet(f"border: 2px solid {cor}; border-radius: 3px;"
                                       if cor else "")

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
        self.cadeado.setPixmap(pixmap("lock_open" if pode else "lock", CORES["titulo"], 16))
        estava_consultando = not self._pode_editar
        for aba in (self.aba_instrumentos, self.aba_calibrar, self.aba_certificados,
                    self.aba_lixeira):
            aba.definir_edicao(pode)
        self._pode_editar = pode
        self._ligar_informar_motivo()
        self.setWindowTitle(self.titulo_janela if pode
                            else f"{self.titulo_janela} — SOMENTE CONSULTA")
        # Quem consulta relê os dados a cada 10 s; quem edita dá sinal a cada 30 s (item 8).
        self.relogio.setInterval(int((INTERVALO_SINAL if pode else INTERVALO_CONSULTA)
                                     .total_seconds() * 1000))
        pede = not pode and self.copia_de is None and self.identidade is not None
        self.botao_pedir.setVisible(pede)
        self.botao_pedir.setEnabled(not self.pedido_enviado)
        self.botao_pedir.setText("Pedido enviado" if self.pedido_enviado else "Pedir edição")
        self.botao_atualizar.setVisible(pede and dono is not None)  # só se outro PC edita
        if pode:
            if estava_consultando and self.identidade is not None:
                # Verde: liberou o pedido ou quem editava saiu (item 7 do teste).
                self.situacao_pedido = "aceito"
                self.mostrar_aviso("✔ Edição liberada: agora você pode editar",
                                   CORES["dentro"], CORES["certo"], 6000)
            self.pedido_enviado = False
            self.rotulo_modo.setText("Modo edição")
            self.rotulo_modo.setCursor(Qt.ArrowCursor)
            self.rotulo_modo.setToolTip("")
            self._contorno_do_modo()
            return
        if self.situacao_pedido == "aceito":
            self.situacao_pedido = ""
        self._contorno_do_modo()
        self.observador.ver(dono.sinal if dono else None, self.agora())
        if self.copia_de is not None:
            self.rotulo_modo.setText("Modo consulta - cópia do banco")
            self.rotulo_modo.setCursor(Qt.ArrowCursor)
            self.rotulo_modo.setToolTip("Este banco é uma cópia: veja o aviso amarelo.")
            return
        texto = f"Modo consulta - {dono.usuario} - {dono.computador}" if dono else "Modo consulta"
        if self.situacao_pedido in ("enviado", "recusado"):
            texto += f" - pedido {self.situacao_pedido}"
        self.rotulo_modo.setText(texto)
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
        self.pedido_enviado, self.situacao_pedido = True, "enviado"
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
            self.pedido_enviado, self.situacao_pedido = False, "recusado"
            self.aplicar_modo(trava)
            self.mostrar_aviso(f"✖ Pedido recusado: {trava.usuario} continua editando",
                               CORES["fora"], CORES["botao"], 6000)

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
        """Quem edita (a cada 30 s) avisa que continua; quem consulta (a cada 10 s) relê os
        dados e passa
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

    def atualizar_agora(self) -> None:
        """Botão "Atualizar" do modo consulta: o mesmo que acontece sozinho a cada 10 s."""
        self.a_cada_sinal()
        if self.repo.modo_consulta:
            self.mostrar_aviso("↻ Atualizado", "#424242", CORES["borda"], 1500)

    def closeEvent(self, evento) -> None:  # noqa: N802 — nome exigido pelo Qt
        self.relogio.stop()
        self.relogio_pedido.stop()
        if self.identidade is not None and not self.repo.modo_consulta:
            self.repo.liberar_trava()
        super().closeEvent(evento)

    def _calibracoes_mudaram(self) -> None:
        """Calibração registrada, corrigida ou na Lixeira: muda cronograma, condição e
        histórico do instrumento."""
        self.atualizar()
        self.aba_instrumentos.recarregar_atual()

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
        with preenchendo(tabela):  # rápido: ajusta as colunas uma vez só
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
        with preenchendo(tabela):  # rápido: ajusta as colunas uma vez só
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
