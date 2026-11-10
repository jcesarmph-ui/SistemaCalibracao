"""Aba Certificados: os PDFs dos certificados das calibrações feitas no programa.

Só código do instrumento | nº do certificado | data da calibração (pedido do usuário em
2026-11-10); clicar na linha ou no botão "Abrir certificado" da linha (pedido de 2026-11-10,
no teste da 1.2.0) abre o PDF no programa de PDF do Windows. Certificados antigos, de
antes do programa, não entram (ficam na pasta física / na DQ05).
"""

from PySide6.QtCore import Qt, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from calibracao.dados.repositorio import Certificado, LinhaCertificado, Repositorio
from calibracao.interface.componentes import (
    RotuloAviso,
    aplicar_destaques,
    celula,
    formatar_data,
    tabela_somente_leitura,
)
from calibracao.interface.estilo import CORES
from calibracao.interface.tema_icones import lupa, por_icone
from calibracao.regras.padronizacao import chave


def abrir_certificado(repositorio: Repositorio, certificado: Certificado) -> tuple[str, str]:
    """Abre o PDF no programa padrão do Windows. Devolve (texto do aviso, tipo): tipo "certo",
    "aviso" (abriu, mas o arquivo foi mexido depois de enviado) ou "erro" (não abriu)."""
    problema = repositorio.conferir_certificado(certificado)
    caminho = repositorio.caminho_do_certificado(certificado)
    if problema and not caminho.is_file():
        return f"✖ {problema}", "erro"
    if not QDesktopServices.openUrl(QUrl.fromLocalFile(str(caminho))):
        return ("✖ O Windows não conseguiu abrir o PDF (há um programa de PDF instalado?).",
                "erro")
    if problema:
        return f"⚠ PDF aberto, mas atenção: {problema}", "aviso"
    return "✔ PDF aberto.", "certo"


class AbaCertificados(QWidget):
    """Lista dos PDFs guardados; abre com um clique. Funciona igual no modo consulta (só lê)."""

    alterado = Signal()  # não grava nada; existe para ficar igual às outras abas

    COLUNAS = ["Código do instrumento", "Nº do certificado", "Data da calibração", ""]

    def __init__(self, repositorio: Repositorio) -> None:
        super().__init__()
        self.repo = repositorio
        self.linhas: list[LinhaCertificado] = []
        self.visiveis: list[LinhaCertificado] = []

        self.busca = QLineEdit(placeholderText="Pesquisar por código ou nº do certificado")
        self.busca.textChanged.connect(self._preencher)
        lupa(self.busca, CORES["dica"])
        self.contagem = QLabel(objectName="dica")
        topo = QHBoxLayout()
        topo.addWidget(self.busca, 1)
        topo.addWidget(QLabel("Clique na linha ou em \"Abrir certificado\". Só aparecem os "
                              "certificados das calibrações registradas no programa.",
                              objectName="dica"), 1)
        topo.addWidget(self.contagem)

        self.tabela = tabela_somente_leitura(self.COLUNAS)
        self.tabela.setProperty("clicavel", True)
        self.tabela.viewport().setCursor(Qt.PointingHandCursor)
        self.tabela.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabela.horizontalHeader().setSectionResizeMode(3, QHeaderView.ResizeToContents)
        self.tabela.clicked.connect(lambda indice: self.abrir_linha(indice.row()))
        self.avisos = RotuloAviso(wordWrap=True, objectName="avisos")

        coluna = QVBoxLayout(self)
        coluna.addLayout(topo)
        coluna.addWidget(self.tabela, 1)
        coluna.addWidget(self.avisos)

    def atualizar(self) -> None:
        self.linhas = self.repo.listar_certificados()
        self._preencher()

    def _preencher(self) -> None:
        termo = chave(self.busca.text())
        self.visiveis = [linha for linha in self.linhas
                         if not termo or termo in chave(f"{linha.codigo} {linha.numero or ''}")]
        self.tabela.setRowCount(len(self.visiveis))
        for numero, linha in enumerate(self.visiveis):
            itens = [celula(linha.codigo), celula(linha.numero or "—"),
                     celula(formatar_data(linha.data_calibracao))]
            for coluna, item in enumerate(itens):
                self.tabela.setItem(numero, coluna, item)
            self.tabela.setItem(numero, 3, celula(""))
        aplicar_destaques(self.tabela)  # antes dos botões: ele tira o que está nas células
        for numero, linha in enumerate(self.visiveis):
            botao = QPushButton("Abrir certificado")
            por_icone(botao, "picture_as_pdf", CORES["titulo"])
            botao.setToolTip(f"Abrir o PDF do certificado de {linha.codigo}")
            botao.clicked.connect(lambda _=False, n=numero: self.abrir_linha(n))
            self.tabela.setCellWidget(numero, 3, botao)
        self.tabela.resizeRowsToContents()
        total = len(self.linhas)
        self.contagem.setText(f"{len(self.visiveis)} de {total}" if termo
                              else f"{total} certificado(s)")
        if not total:
            self._aviso("Nenhum PDF guardado ainda. Ele é escolhido na Nova calibração ou no "
                        "EDITAR da calibração (aba Calibrar).")
        elif self.avisos.text().startswith("Nenhum PDF"):
            self._aviso("")

    def abrir_linha(self, numero: int) -> None:
        if not 0 <= numero < len(self.visiveis):
            return
        certificado = self.repo.obter_certificado(self.visiveis[numero].certificado_id)
        texto, tipo = abrir_certificado(self.repo, certificado)
        self._aviso(texto, tipo)

    def definir_edicao(self, pode: bool) -> None:
        """Nada a esconder: a aba só abre PDFs."""

    def _aviso(self, texto: str, tipo: str = "dica") -> None:
        cor = {"certo": CORES["certo"], "erro": CORES["erro"], "aviso": CORES["aviso"]}.get(
            tipo, CORES["dica"])
        self.avisos.setStyleSheet(f"color: {cor};")
        self.avisos.setText(texto)
