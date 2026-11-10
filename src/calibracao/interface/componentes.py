"""Peças de tela usadas em mais de uma aba."""

import contextlib
import datetime
import difflib

from PySide6.QtCore import (
    QEvent,
    QObject,
    QPoint,
    QSize,
    QStringListModel,
    Qt,
    QTimer,
    Signal,
)
from PySide6.QtGui import QColor, QTextCharFormat
from PySide6.QtWidgets import (
    QAbstractButton,
    QAbstractItemDelegate,
    QAbstractItemView,
    QAbstractScrollArea,
    QAbstractSpinBox,
    QApplication,
    QCalendarWidget,
    QComboBox,
    QCompleter,
    QDialog,
    QFrame,
    QGroupBox,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTabBar,
    QTableWidget,
    QTableWidgetItem,
    QToolButton,
    QVBoxLayout,
    QWidget,
)

from calibracao.interface.estilo import CORES, abreviar_indicativa, destacar, tem_destaque
from calibracao.interface.tema_icones import html_com_icones, icone
from calibracao.regras.padronizacao import chave, locais


class FiltroRodaDoMouse(QObject):
    """A roda do mouse só rola a tela: nunca troca opção, data ou aba (pedido de 2026-10-30).

    Em cima de lista de opções, campo de data/número ou barra de abas, a rolagem vai para quem
    está por trás (a tabela ou a página), que sobe e desce normalmente.
    """

    SEM_RODA = (QComboBox, QAbstractSpinBox, QTabBar)
    # Mãozinha em tudo o que é clicável (pedido de 2026-11-03); desligado fica com a seta.
    CLICAVEIS = (QAbstractButton, QComboBox, QTabBar)

    ENTER = (Qt.Key_Return, Qt.Key_Enter)

    def eventFilter(self, objeto, evento) -> bool:  # noqa: N802 — nome exigido pelo Qt
        if (evento.type() in (QEvent.Polish, QEvent.EnabledChange)
                and isinstance(objeto, self.CLICAVEIS)):
            objeto.setCursor(Qt.PointingHandCursor if objeto.isEnabled() else Qt.ArrowCursor)
        if evento.type() == QEvent.Polish and isinstance(objeto, QCalendarWidget):
            calendario_escuro(objeto)
        if evento.type() == QEvent.KeyPress and self._tecla_de_fechar(objeto, evento):
            return True
        if (evento.type() == QEvent.Wheel and evento.modifiers() & Qt.ShiftModifier
                and self._rolar_para_o_lado(objeto, evento)):
            return True
        if evento.type() == QEvent.Wheel and isinstance(objeto, self.SEM_RODA):
            pai = objeto.parentWidget()
            if pai is not None:
                QApplication.sendEvent(pai, evento)
            return True
        return False

    def _tecla_de_fechar(self, objeto, evento) -> bool:
        """Janela só fecha pelo X, por Salvar ou por Cancelar (pedido de 2026-11-04: o Enter
        fechou a calibração e tudo o que estava digitado se perdeu).

        Enter ou Esc que nenhum campo usou "sobe" até a janela, que apertaria o botão padrão
        (Enter) ou fecharia (Esc): ali eles param. Enter também não aperta botão nenhum.
        """
        if evento.key() == Qt.Key_Escape:
            return isinstance(objeto, QDialog)
        return evento.key() in self.ENTER and isinstance(objeto, (QDialog, QPushButton))

    @staticmethod
    def _rolar_para_o_lado(objeto, evento) -> bool:
        """Shift + roda = rolar para os lados (pedido de 2026-11-03), na primeira área com barra
        horizontal a partir de onde está o mouse."""
        passo = evento.angleDelta().y() or evento.angleDelta().x()
        widget = objeto if isinstance(objeto, QWidget) else None
        while widget is not None:
            if isinstance(widget, QAbstractScrollArea):
                barra = widget.horizontalScrollBar()
                if barra.maximum() > barra.minimum():
                    barra.setValue(barra.value() - round(passo / 120 * barra.singleStep() * 3))
                    return True
            widget = widget.parentWidget()
        return False


def instalar_filtro_roda() -> None:
    """Liga o filtro (roda do mouse, mãozinha, Enter/Esc que não fecham janela e calendário
    escuro) para o programa inteiro (janelas e diálogos), uma vez só."""
    app = QApplication.instance()
    if app is not None and not hasattr(app, "_filtro_roda"):
        app._filtro_roda = FiltroRodaDoMouse(app)
        app.installEventFilter(app._filtro_roda)


def calendario_escuro(calendario: QCalendarWidget) -> None:
    """Calendário das datas no tema escuro (o resto vem do estilo): fim de semana na mesma cor
    dos outros dias (vermelho é só para erro) e sem a coluna do número da semana."""
    calendario.setVerticalHeaderFormat(QCalendarWidget.NoVerticalHeader)
    formato = QTextCharFormat()
    formato.setForeground(QColor("#f0f0f0"))
    for dia in (Qt.Saturday, Qt.Sunday):
        calendario.setWeekdayTextFormat(dia, formato)


class _EnterDesce(QObject):
    """Enter na tabela confirma o valor e vai para a célula de baixo, igual ao Excel (pedido de
    2026-11-04). Pula as células que não se digitam; na última, fica onde está."""

    def __init__(self, tabela: QTableWidget) -> None:
        super().__init__(tabela)
        self.tabela = tabela
        # O Enter que confirmou a célula continua "subindo" até a tabela: não desce de novo.
        self._descida_marcada = False
        tabela.installEventFilter(self)
        tabela.itemDelegate().closeEditor.connect(self._fechou_editor)

    def eventFilter(self, objeto, evento) -> bool:  # noqa: N802 — nome exigido pelo Qt
        if (evento.type() == QEvent.KeyPress and evento.key() in (Qt.Key_Return, Qt.Key_Enter)
                and self.tabela.state() != QAbstractItemView.EditingState):
            if not self._descida_marcada:
                self.descer()
            return True
        return False

    def _fechou_editor(self, _editor, dica) -> None:
        # Enter ao digitar fecha o editor com SubmitModelCache (Tab e clique fora, não).
        if dica == QAbstractItemDelegate.SubmitModelCache:
            self._descida_marcada = True
            # A linha de onde saiu: ao fechar o editor, o foco pode cair numa caixa de escolha
            # de outra linha e mudar a célula atual antes de descer.
            atual = self.tabela.currentIndex()
            QTimer.singleShot(0, lambda: self.descer(atual.row(), atual.column()))

    def descer(self, linha_atual: int | None = None, coluna: int | None = None) -> None:
        self._descida_marcada = False
        tabela = self.tabela
        if linha_atual is None:
            atual = tabela.currentIndex()
            if not atual.isValid():
                return
            linha_atual, coluna = atual.row(), atual.column()
        if linha_atual < 0:
            return
        for linha in range(linha_atual + 1, tabela.rowCount()):
            widget = tabela.cellWidget(linha, coluna)
            if widget is not None and widget.isEnabled() and widget.focusPolicy() != Qt.NoFocus:
                tabela.setCurrentCell(linha, coluna)
                widget.setFocus()
                return
            item = tabela.item(linha, coluna)
            if item is not None and item.flags() & Qt.ItemIsEditable:
                tabela.setCurrentCell(linha, coluna)
                if tabela.editTriggers() != QAbstractItemView.NoEditTriggers:
                    tabela.editItem(item)
                return


def enter_desce(tabela: QTableWidget) -> None:
    tabela._enter_desce = _EnterDesce(tabela)


def data_livre_para_tela(texto: str | None) -> str:
    """Data guardada como aaaa-mm-dd aparece como dd/mm/aaaa; qualquer outro texto (ex.: "-" ou
    uma frase vinda da planilha) aparece como está."""
    if not texto:
        return ""
    try:
        return datetime.date.fromisoformat(texto.strip()).strftime("%d/%m/%Y")
    except ValueError:
        return texto


def data_livre_para_banco(texto: str | None) -> str | None:
    """O contrário: dd/mm/aaaa vira aaaa-mm-dd (como as datas já guardadas); o resto fica igual."""
    texto = (texto or "").strip()
    if not texto:
        return None
    try:
        return datetime.datetime.strptime(texto, "%d/%m/%Y").date().isoformat()
    except ValueError:
        return texto


class BotaoCalendario(QToolButton):
    """Ícone de calendário ao lado de um campo de texto de data (pedido de 2026-11-10; ícone
    "calendar_month" do Google): abre o mesmo calendário das outras datas e escreve o dia
    escolhido (dd/mm/aaaa) no campo. O campo continua aceitando digitação."""

    def __init__(self, campo, parent=None) -> None:
        super().__init__(parent)
        self.campo = campo
        self.setObjectName("calendario")
        self.setIcon(icone("calendar_month", CORES["titulo"]))
        self.setIconSize(QSize(24, 24))
        self.setToolTip("Abrir o calendário (ou digite a data no campo, dd/mm/aaaa).")
        self.calendario = QCalendarWidget()
        self.calendario.setWindowFlags(Qt.Popup)
        self.calendario.setGridVisible(False)
        self.calendario.clicked.connect(self._escolheu)
        self.clicked.connect(self.abrir)

    def setEnabled(self, ligado: bool) -> None:  # noqa: N802 — nome do Qt
        super().setEnabled(ligado)
        self.setVisible(ligado)  # campo só de consulta: o ícone some

    def abrir(self) -> None:
        texto = self.campo.text().strip()
        try:
            dia = datetime.datetime.strptime(texto, "%d/%m/%Y").date()
        except ValueError:
            dia = datetime.date.today()
        self.calendario.setSelectedDate(dia)
        self.calendario.adjustSize()
        self.calendario.move(self.campo.mapToGlobal(QPoint(0, self.campo.height())))
        self.calendario.show()

    def _escolheu(self, data) -> None:
        self.campo.setText(data.toPython().strftime("%d/%m/%Y"))
        self.calendario.hide()


def dinheiro(valor: float | None) -> str:
    """R$ com centavos e ponto no milhar (ex.: R$ 1.350,00)."""
    if valor is None:
        return "—"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def reais_em_texto(valor: float | None) -> str:
    """Valor em reais para o campo de digitar, sempre com os centavos (ex.: 350,00)."""
    return "" if valor is None else f"{valor:.2f}".replace(".", ",")


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
            if abreviar_indicativa(item.text()):
                # "IND.": o texto inteiro ao passar o mouse; a coluna se ajusta ao curto
                rotulo.setToolTip(item.text())
                item.setSizeHint(rotulo.sizeHint())
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


def altura_do_conteudo(tabela: QTableWidget, linhas_minimas: int = 3) -> None:
    """A tabela fica da altura das linhas que tem (no mínimo `linhas_minimas`), para o que vem
    logo abaixo dela — ex.: os botões da Lixeira — ficar perto (pedido de 2026-11-03). Com
    muitas linhas, cresce até o espaço da tela e rola."""
    linhas = max(tabela.rowCount(), linhas_minimas)
    altura = tabela.horizontalHeader().height() + 4
    altura += sum(tabela.rowHeight(n) for n in range(tabela.rowCount()))
    altura += (linhas - tabela.rowCount()) * tabela.verticalHeader().defaultSectionSize()
    if tabela.horizontalScrollBar().isVisible():
        altura += tabela.horizontalScrollBar().height()
    tabela.setMaximumHeight(altura)


@contextlib.contextmanager
def preenchendo(tabela: QTableWidget):
    """Preencher muitas linhas de uma vez: a tabela não se redesenha nem recalcula a largura das
    colunas a cada célula, só uma vez no fim (era o que deixava a tela lenta depois de salvar,
    achado em 2026-11-03)."""
    cabecalho = tabela.horizontalHeader()
    modos = [cabecalho.sectionResizeMode(n) for n in range(tabela.columnCount())]
    tabela.setUpdatesEnabled(False)
    cabecalho.setSectionResizeMode(QHeaderView.Interactive)
    try:
        yield
    finally:
        for coluna, modo in enumerate(modos):
            cabecalho.setSectionResizeMode(coluna, modo)
        tabela.setUpdatesEnabled(True)


class CampoComSugestoes(QLineEdit):
    """Campo de texto com sugestões enquanto se digita, como a pesquisa do Google (pedido de
    2026-11-10): mostra os nomes já usados que têm o que foi digitado em qualquer parte, sem ligar
    para maiúsculas nem acentos ("paqui" acha "Paquímetro"). Clicar (ou Enter) numa sugestão
    escreve o nome do jeito certo. Dá para escrever um nome novo, mas `nomes_novos` diz quais não
    existem, para a tela avisar e pedir confirmação.

    Com `varios=True` (localização) aceita mais de um nome separado por " / ": as sugestões valem
    para o trecho depois da última barra.
    """

    def __init__(self, varios: bool = False, parent=None) -> None:
        super().__init__(parent)
        self.varios = varios
        self.opcoes: list[str] = []
        self._modelo = QStringListModel(self)
        self.sugestoes = QCompleter(self._modelo, self)
        self.sugestoes.setWidget(self)
        self.sugestoes.setCompletionMode(QCompleter.UnfilteredPopupCompletion)
        self.sugestoes.setMaxVisibleItems(12)
        self.sugestoes.popup().setObjectName("sugestoes")  # tema escuro (estilo.py)
        self.sugestoes.activated.connect(self.escolher)
        self.textEdited.connect(self.mostrar_sugestoes)

    def definir_opcoes(self, opcoes: list[str]) -> None:
        self.opcoes = list(opcoes)

    def _trecho(self) -> tuple[str, str]:
        """(o que vem antes, o trecho que está sendo digitado)."""
        texto = self.text()
        if self.varios and "/" in texto:
            antes, _, trecho = texto.rpartition("/")
            return antes.rstrip() + " / ", trecho.strip()
        return "", texto.strip()

    def filtradas(self) -> list[str]:
        _, trecho = self._trecho()
        procurado = chave(trecho)
        return [opcao for opcao in self.opcoes if procurado in chave(opcao)]

    def mostrar_sugestoes(self, _texto: str = "") -> None:
        filtradas = self.filtradas()
        self._modelo.setStringList(filtradas)
        if filtradas:
            self.sugestoes.complete()
        else:
            self.sugestoes.popup().hide()

    def escolher(self, opcao: str) -> None:
        antes, _ = self._trecho()
        self.setText(antes + opcao)
        self.sugestoes.popup().hide()

    def mais_um(self) -> None:
        """Botão "Mais um local": põe a barra e já mostra todas as opções."""
        texto = self.text().rstrip()
        if texto and not texto.endswith("/"):
            self.setText(texto + " / ")
        self.setFocus()
        self.mostrar_sugestoes()

    def nomes(self) -> list[str]:
        if not self.text().strip():
            return []
        return locais(self.text()) if self.varios else [" ".join(self.text().split())]

    def nomes_novos(self) -> list[str]:
        """Os nomes digitados que nenhum instrumento usa ainda."""
        existentes = {chave(opcao) for opcao in self.opcoes}
        return [nome for nome in self.nomes() if chave(nome) not in existentes]

    def parecidos(self, nome: str) -> list[str]:
        """Nomes já usados parecidos com um nome novo ("CT - 1" → "CT-01")."""
        k = chave(nome)
        compactos = {o: chave(o).replace(" ", "").replace("-", "") for o in self.opcoes}
        k_compacto = k.replace(" ", "").replace("-", "")
        achados = [o for o in self.opcoes
                   if k and (k in chave(o) or chave(o) in k
                             or difflib.SequenceMatcher(None, k_compacto,
                                                        compactos[o]).ratio() >= 0.75)]
        return achados[:4]

    def aviso_de_novos(self, oque: str) -> str:
        """Texto do aviso amarelo para os nomes novos (vazio se não há). Enquanto o que foi
        digitado ainda é pedaço de um nome da lista ("serra" de "Serralheria"), não avisa: a
        pessoa provavelmente ainda vai escolher na lista (ao salvar, a pergunta vale igual)."""
        partes = []
        for nome in self.nomes_novos():
            if any(chave(nome) in chave(opcao) for opcao in self.opcoes):
                continue
            parecidos = self.parecidos(nome)
            parece = (f" Parece com: {', '.join(parecidos)} — se for o mesmo, escolha na lista."
                      if parecidos else "")
            partes.append(f"⚠ \"{nome}\" é {oque} novo (nenhum instrumento usa).{parece}")
        return "\n".join(partes)


# Símbolos dos avisos → ícone do Google na cor do aviso (aprovado por foto em 2026-11-10).
SIMBOLOS = {"✔": ("check_circle", CORES["certo"]), "✖": ("error", CORES["erro"]),
            "⚠": ("warning", CORES["aviso"])}


class RotuloAviso(QLabel):
    """Rótulo de aviso: ✔ ✖ ⚠ no começo da frase aparecem como ícone (verde, vermelho, amarelo).

    O texto continua guardado como foi escrito (`text()` devolve com o símbolo); só a tela mostra
    o ícone. `cor_icone` pinta todos de uma cor só (ex.: branco no aviso flutuante colorido).
    """

    def __init__(self, texto: str = "", parent=None, cor_icone: str | None = None, **kw) -> None:
        super().__init__(parent, **kw)
        self.cor_icone = cor_icone
        self._original = ""
        self.setText(texto)

    def setText(self, texto: str) -> None:  # noqa: N802 — nome do Qt
        self._original = texto
        simbolos = ({s: (nome, self.cor_icone) for s, (nome, _) in SIMBOLOS.items()}
                    if self.cor_icone else SIMBOLOS)
        com_icones = html_com_icones(texto, simbolos)
        self.setTextFormat(Qt.RichText if com_icones else Qt.AutoText)
        super().setText(com_icones if com_icones else texto)

    def text(self) -> str:
        return self._original
