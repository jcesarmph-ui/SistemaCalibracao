"""Aba Relatórios (pedido de 2026-11-10): o relatório do mês atual (muda sozinho — é montado na
hora de abrir), o último relatório final guardado, o relatório do ano atual e a lista dos
relatórios guardados. Na lista, só o botão "Abrir PDF" da linha abre o relatório.

O relatório final de cada mês (e de cada ano) que acabou é guardado sozinho pela janela
principal, na primeira abertura do programa no mês novo (`guardar_pendentes`).
"""

import datetime

from PySide6.QtCore import QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import (
    QAbstractItemView,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from calibracao.dados.repositorio import ErroDeValidacao, RelatorioGuardado, Repositorio
from calibracao.interface.componentes import RotuloAviso, celula, tabela_somente_leitura
from calibracao.interface.estilo import CORES
from calibracao.interface.tema_icones import por_icone
from calibracao.regras import relatorio as regras
from calibracao.regras.relatorio import Periodo


def montar_pdf(repositorio: Repositorio, periodo: Periodo, hoje: datetime.date, destino):
    """Junta o conteúdo do banco e os gráficos do painel e escreve o PDF."""
    from calibracao.interface.relatorio_pdf import gerar_pdf  # carrega o Matplotlib

    conteudo = repositorio.conteudo_do_relatorio(periodo, hoje, datetime.datetime.now())
    calibracoes, instrumentos = repositorio.dados_dos_indicadores()
    graficos = [definicao for _, definicao in repositorio.listar_graficos()]
    return gerar_pdf(conteudo, graficos, calibracoes, instrumentos, destino)


def guardar_pendentes(repositorio: Repositorio, hoje: datetime.date, usuario: str | None) -> int:
    """Guarda o relatório final de cada mês/ano que acabou e ainda não foi guardado (sem
    perguntar nada). Devolve quantos guardou. Só no modo edição (o banco recusa no consulta)."""
    import tempfile
    from pathlib import Path

    guardados = 0
    for periodo in repositorio.relatorios_pendentes(hoje):
        temporario = Path(tempfile.mkdtemp()) / periodo.nome_do_arquivo()
        montar_pdf(repositorio, periodo, hoje, temporario)
        repositorio.guardar_relatorio(periodo, temporario, usuario, datetime.datetime.now())
        temporario.unlink(missing_ok=True)
        guardados += 1
    return guardados


def abrir_arquivo(caminho) -> bool:
    return QDesktopServices.openUrl(QUrl.fromLocalFile(str(caminho)))


class AbaRelatorios(QWidget):
    alterado = Signal()

    COLUNAS = ["Relatório", "Período", "Guardado em", ""]

    def __init__(self, repositorio: Repositorio, hoje: datetime.date) -> None:
        super().__init__()
        self.repo = repositorio
        self.hoje = hoje
        self.guardados: list[RelatorioGuardado] = []

        caixa_mes = QGroupBox("Relatório do mês atual")
        self.texto_mes = QLabel(wordWrap=True)
        self.abrir_mes = QPushButton("ABRIR RELATÓRIO DO MÊS ATUAL", objectName="principal")
        self.abrir_mes.setToolTip("Monta agora o relatório do mês com tudo o que já foi feito "
                                  "(muda a cada calibração ou alteração).")
        self.abrir_mes.clicked.connect(lambda: self.abrir_atual(regras.mes_atual(self.hoje)))
        coluna = QVBoxLayout(caixa_mes)
        coluna.addWidget(self.texto_mes)
        coluna.addWidget(self.abrir_mes)

        caixa_final = QGroupBox("Relatório final do mês que acabou")
        self.texto_final = QLabel(wordWrap=True)
        self.abrir_final = QPushButton()
        por_icone(self.abrir_final, "picture_as_pdf", CORES["titulo"])
        self.abrir_final.clicked.connect(lambda: self.abrir_guardado(self._ultimo_mensal()))
        coluna = QVBoxLayout(caixa_final)
        coluna.addWidget(self.texto_final)
        coluna.addWidget(self.abrir_final)

        caixa_ano = QGroupBox("Relatório do ano")
        self.texto_ano = QLabel(wordWrap=True)
        self.abrir_ano = QPushButton(f"Abrir relatório de {hoje.year} (até agora)")
        por_icone(self.abrir_ano, "picture_as_pdf", CORES["titulo"])
        self.abrir_ano.setToolTip("Monta agora o relatório do ano até hoje. O do ano só fica "
                                  "guardado quando o ano acabar.")
        self.abrir_ano.clicked.connect(lambda: self.abrir_atual(regras.ano_atual(self.hoje)))
        coluna = QVBoxLayout(caixa_ano)
        coluna.addWidget(self.texto_ano)
        coluna.addWidget(self.abrir_ano)

        faixa = QHBoxLayout()
        for caixa in (caixa_mes, caixa_final, caixa_ano):
            faixa.addWidget(caixa, 1)

        self.tabela = tabela_somente_leitura(self.COLUNAS)
        self.tabela.setSelectionMode(QAbstractItemView.NoSelection)
        cabecalho = self.tabela.horizontalHeader()
        cabecalho.setSectionResizeMode(QHeaderView.Stretch)
        cabecalho.setSectionResizeMode(3, QHeaderView.ResizeToContents)
        lista = QGroupBox("Relatórios guardados")
        coluna = QVBoxLayout(lista)
        self.dica_lista = QLabel(objectName="dica")
        coluna.addWidget(self.dica_lista)
        coluna.addWidget(self.tabela)
        self.avisos = RotuloAviso(wordWrap=True, objectName="avisos")

        tela = QVBoxLayout(self)
        tela.addLayout(faixa)
        tela.addWidget(lista, 1)
        tela.addWidget(self.avisos)

    def atualizar(self) -> None:
        self.guardados = self.repo.relatorios_guardados()
        mes = regras.mes_atual(self.hoje)
        self.texto_mes.setText(f"<b>{mes.nome.capitalize()}</b> — em andamento: muda sozinho a "
                               "cada calibração ou alteração. Vira o relatório final quando o "
                               "mês acabar.")
        ultimo = self._ultimo_mensal()
        if ultimo:
            self.texto_final.setText(f"<b>{ultimo.periodo.nome.capitalize()}</b> — guardado "
                                     f"sozinho em {ultimo.gerado_em:%d/%m/%Y %H:%M} (não muda "
                                     "mais).")
            self.abrir_final.setText(f"Abrir relatório final de {ultimo.periodo.nome}")
        else:
            self.texto_final.setText("Ainda não há: o primeiro é guardado sozinho quando o "
                                     "primeiro mês de uso do programa acabar.")
            self.abrir_final.setText("Abrir relatório final")
        self.abrir_final.setEnabled(ultimo is not None)
        self.texto_ano.setText(f"<b>{self.hoje.year}</b> — até agora (o do ano fica guardado "
                               "quando o ano acabar).")
        self.tabela.setRowCount(len(self.guardados))
        for linha, relatorio in enumerate(self.guardados):
            valores = [relatorio.periodo.tipo, relatorio.periodo.nome,
                       f"{relatorio.gerado_em:%d/%m/%Y %H:%M}"]
            for coluna, valor in enumerate(valores):
                self.tabela.setItem(linha, coluna, celula(valor))
            botao = QPushButton("Abrir PDF")
            por_icone(botao, "picture_as_pdf", CORES["titulo"])
            botao.setToolTip(f"Abrir o relatório de {relatorio.periodo.nome}")
            botao.clicked.connect(lambda _=False, r=relatorio: self.abrir_guardado(r))
            self.tabela.setCellWidget(linha, 3, botao)
        self.tabela.resizeRowsToContents()
        self.dica_lista.setText("Para abrir, clique em \"Abrir PDF\" na linha." if self.guardados
                                else "Nenhum relatório guardado ainda.")

    def _ultimo_mensal(self) -> RelatorioGuardado | None:
        mensais = [r for r in self.guardados if r.periodo.tipo == regras.MENSAL]
        return max(mensais, key=lambda r: r.periodo.chave) if mensais else None

    # --- abrir ------------------------------------------------------------------------------
    def abrir_atual(self, periodo: Periodo) -> None:
        """Monta o relatório agora (pasta temporária) e abre."""
        from calibracao.interface.relatorio_pdf import nome_temporario

        try:
            caminho = montar_pdf(self.repo, periodo, self.hoje, nome_temporario(periodo.chave))
        except OSError as erro:
            self._aviso(f"✖ Não foi possível montar o relatório: {erro}", erro=True)
            return
        if abrir_arquivo(caminho):
            self._aviso(f"✔ Relatório de {periodo.nome} aberto.", certo=True)
        else:
            self._aviso("✖ O Windows não conseguiu abrir o PDF (há um programa de PDF "
                        "instalado?).", erro=True)

    def abrir_guardado(self, relatorio: RelatorioGuardado | None) -> None:
        if relatorio is None:
            return
        try:
            problema = self.repo.conferir_relatorio(relatorio)
            caminho = self.repo.caminho_do_relatorio(relatorio)
        except ErroDeValidacao as erro:
            self._aviso("\n".join(f"✖ {m}" for m in erro.mensagens), erro=True)
            return
        if problema and not caminho.is_file():
            self._aviso(f"✖ {problema}", erro=True)
            return
        if not abrir_arquivo(caminho):
            self._aviso("✖ O Windows não conseguiu abrir o PDF.", erro=True)
            return
        if problema:
            self._aviso(f"⚠ PDF aberto, mas atenção: {problema}")
        else:
            self._aviso(f"✔ Relatório de {relatorio.periodo.nome} aberto.", certo=True)

    def definir_edicao(self, pode: bool) -> None:
        """Nada a esconder: a aba só abre relatórios."""

    def _aviso(self, texto: str, certo: bool = False, erro: bool = False) -> None:
        cor = CORES["erro"] if erro else CORES["certo"] if certo else CORES["aviso"]
        self.avisos.setStyleSheet(f"color: {cor};")
        self.avisos.setText(texto)
