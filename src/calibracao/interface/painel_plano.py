"""Plano de calibração do instrumento: tabela de pontos editável direto nas células.

É por aqui que o usuário corrige o que veio da planilha DQ05 e preenche as incertezas (U) que
faltam. Mudar o plano vale daqui para a frente: calibrações já feitas guardam a "foto" antiga.
"""

import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from calibracao.dados.repositorio import ErroDeValidacao, PontoPlano, Repositorio
from calibracao.regras.lixeira import Tipo

# Tipos de ponto com nome amigável (o banco guarda a sigla da esquerda).
TIPOS = {
    "NUMERICO": ("Numérico", "Nominal ± tolerância (ou o erro do certificado, sem nominal)."),
    "LIMITE": ("Limite", "Valor mínimo e/ou máximo (ex.: Planeza 2 µm máx)."),
    "CLASSE": ("Classe", "Classe exigida; o resultado é escolhido olhando o certificado."),
    "CRITERIO": ("Critério", "Texto a atender (ex.: Executa função)."),
    "VERIFICACAO": ("Verificação visual", "Item a conferir (ex.: Aspecto geral)."),
}

# (atributo do ponto, título da coluna, é número?, dica ao passar o mouse)
COLUNAS = [
    ("ordem", "Nº", True, "Ordem do ponto no plano."),
    ("secao", "Seção", False, "Agrupamento do ponto (ex.: Face Externa, Antes do ajuste)."),
    ("tipo", "Tipo", False, "Como o ponto é avaliado."),
    ("descricao", "Descrição", False, "Nome do ponto (ex.: 60,00 ou Aspecto geral)."),
    ("valor_nominal", "Nominal", True, "Valor de referência. Vazio = sem nominal fixo: na "
                                        "calibração se digita o erro do certificado."),
    ("unidade", "Unidade", False, ""),
    ("tolerancia_inferior", "Tol. inferior", True, "Ex.: −0,05 (para ± 0,05)."),
    ("tolerancia_superior", "Tol. superior", True, "Ex.: 0,05 (para ± 0,05)."),
    ("valor_minimo", "Mínimo", True, "Pontos de limite: valor mínimo aceito."),
    ("valor_maximo", "Máximo", True, "Pontos de limite: valor máximo aceito."),
    ("classe_exigida", "Classe exigida", False, ""),
    ("criterio", "Critério", False, "Texto a atender (ex.: Executa função)."),
    ("incerteza", "Incerteza (U)", True,
     "Incerteza expandida de medição: quanto o resultado pode variar para mais ou para menos. "
     "Sem ela o ponto fica \"não avaliado\" e a calibração não pode ser salva."),
]
_COLUNA = {nome: indice for indice, (nome, *_) in enumerate(COLUNAS)}


def numero(texto: str) -> float | None:
    """Aceita vírgula ou ponto; vazio = None. ValueError se não for número."""
    texto = texto.strip().replace("±", "").replace(" ", "").replace(",", ".")
    return float(texto) if texto else None


def numero_em_texto(valor: float | None) -> str:
    if valor is None:
        return ""
    return f"{valor:.6f}".rstrip("0").rstrip(".").replace(".", ",")


class PainelPlano(QWidget):
    alterado = Signal()

    def __init__(self, repositorio: Repositorio) -> None:
        super().__init__()
        self.repo = repositorio
        self.plano_id: int | None = None
        self._pontos: list[PontoPlano] = []
        self.pode_editar = True

        self.titulo = QLabel(objectName="dica")
        self.tabela = QTableWidget(0, len(COLUNAS))
        self.tabela.verticalHeader().setVisible(False)
        for indice, (_, titulo, _, dica) in enumerate(COLUNAS):
            item = QTableWidgetItem(titulo)
            item.setToolTip(dica)
            self.tabela.setHorizontalHeaderItem(indice, item)
        self._gatilhos_edicao = self.tabela.editTriggers()  # volta a eles ao sair da consulta
        cabecalho = self.tabela.horizontalHeader()
        # Cada coluna do tamanho do conteúdo (rola para o lado se precisar); a última completa.
        cabecalho.setSectionResizeMode(QHeaderView.ResizeToContents)
        cabecalho.setStretchLastSection(True)

        self.adicionar = QPushButton("Adicionar ponto")
        self.adicionar.clicked.connect(self.adicionar_ponto)
        self.remover = QPushButton("Enviar ponto para a Lixeira")
        self.remover.clicked.connect(self.remover_ponto)
        self.salvar = QPushButton("Salvar alterações do plano")
        self.salvar.clicked.connect(self.salvar_plano)
        botoes = QHBoxLayout()
        botoes.addWidget(self.adicionar)
        botoes.addWidget(self.remover)
        botoes.addStretch()
        botoes.addWidget(self.salvar)
        self.avisos = QLabel(wordWrap=True)

        coluna = QVBoxLayout(self)
        coluna.addWidget(self.titulo)
        coluna.addWidget(self.tabela, 1)
        coluna.addWidget(self.avisos)
        coluna.addLayout(botoes)
        self.mostrar(None)

    def mostrar(self, plano_id: int | None) -> None:
        self.plano_id = plano_id
        self._pontos = self.repo.listar_pontos(plano_id) if plano_id else []
        self.tabela.setRowCount(0)
        for ponto in self._pontos:
            self._nova_linha(ponto)
        sem_u = sum(1 for p in self._pontos if p.tipo in ("NUMERICO", "LIMITE")
                    and p.incerteza is None)
        if plano_id is None:
            self.titulo.setText("Este instrumento não tem plano: escolha um plano nos dados "
                                "acima e clique em SALVAR." if self.pode_editar
                                else "Este instrumento não tem plano de calibração.")
        else:
            nome = self.repo.obter_plano(plano_id).nome
            self.titulo.setText(f"{nome}: {len(self._pontos)} ponto(s). "
                                + ("Clique duas vezes numa célula para editar."
                                   if self.pode_editar else "(somente consulta)"))
        for botao in (self.adicionar, self.remover, self.salvar):
            botao.setEnabled(plano_id is not None)
        self._aviso(f"⚠ {sem_u} ponto(s) sem Incerteza (U): preencha antes de registrar a "
                    "calibração." if sem_u else "")

    def _nova_linha(self, ponto: PontoPlano) -> None:
        linha = self.tabela.rowCount()
        self.tabela.insertRow(linha)
        for indice, (nome, _, eh_numero, _) in enumerate(COLUNAS):
            if nome == "tipo":
                escolha = QComboBox()
                for sigla, (texto, dica) in TIPOS.items():
                    escolha.addItem(texto, sigla)
                    escolha.setItemData(escolha.count() - 1, dica, Qt.ToolTipRole)
                escolha.setCurrentIndex(max(escolha.findData(ponto.tipo), 0))
                escolha.setEnabled(self.pode_editar)
                self.tabela.setCellWidget(linha, indice, escolha)
                continue
            valor = getattr(ponto, nome)
            texto = (str(valor) if nome == "ordem" and valor is not None
                     else numero_em_texto(valor) if eh_numero else (valor or ""))
            item = QTableWidgetItem(texto)
            if nome == "incerteza" and ponto.tipo in ("NUMERICO", "LIMITE") and valor is None:
                item.setBackground(Qt.yellow)  # aviso: falta a U
                item.setForeground(Qt.black)
            self.tabela.setItem(linha, indice, item)
        self.tabela.item(linha, 0).setData(Qt.UserRole, ponto.id)

    # --- Ações ------------------------------------------------------------------------------

    def adicionar_ponto(self) -> None:
        proxima = max((p.ordem or 0 for p in self._pontos), default=0) + 1
        self._nova_linha(PontoPlano(self.plano_id, "NUMERICO", "", ordem=proxima))
        self.tabela.scrollToBottom()
        self.tabela.editItem(self.tabela.item(self.tabela.rowCount() - 1, _COLUNA["descricao"]))
        self._aviso("Preencha o ponto novo e clique em \"Salvar alterações do plano\".")

    def _ponto_da_linha(self, linha: int) -> PontoPlano:
        dados = {"plano_id": self.plano_id, "id": self.tabela.item(linha, 0).data(Qt.UserRole)}
        for indice, (nome, titulo, eh_numero, _) in enumerate(COLUNAS):
            if nome == "tipo":
                dados[nome] = self.tabela.cellWidget(linha, indice).currentData()
                continue
            texto = self.tabela.item(linha, indice).text()
            if nome == "ordem":
                if not texto.strip().isdigit():
                    raise ValueError(f"Linha {linha + 1}: o Nº deve ser um número inteiro.")
                dados[nome] = int(texto)
            elif eh_numero:
                try:
                    dados[nome] = numero(texto)
                except ValueError:
                    raise ValueError(f"Linha {linha + 1}: \"{texto}\" em {titulo} não é um "
                                     "número.") from None
            else:
                dados[nome] = texto.strip() or None
        dados["descricao"] = dados["descricao"] or ""
        # O nº original da planilha não aparece na tabela: mantém o que está guardado.
        salvo = next((p for p in self._pontos if p.id == dados["id"]), None)
        dados["ordem_original"] = salvo.ordem_original if salvo else None
        return PontoPlano(**dados)

    def tem_alteracao(self) -> bool:
        """Algo digitado na tabela e ainda não salvo (ponto novo, mudado ou inválido)."""
        antigos = {p.id: p for p in self._pontos}
        for linha in range(self.tabela.rowCount()):
            try:
                ponto = self._ponto_da_linha(linha)
            except ValueError:
                return True
            if ponto.id is None or ponto != antigos.get(ponto.id):
                return True
        return False

    def salvar_plano(self) -> None:
        erros, pontos = [], []
        for linha in range(self.tabela.rowCount()):
            try:
                pontos.append(self._ponto_da_linha(linha))
            except ValueError as erro:
                erros.append(str(erro))
        if erros:
            self._aviso("\n".join(f"✖ {e}" for e in erros), erro=True)
            return
        antigos = {p.id: p for p in self._pontos}
        try:
            for ponto in pontos:
                if ponto.id is None:
                    self.repo.incluir_ponto(ponto)
                elif ponto != antigos.get(ponto.id):
                    self.repo.atualizar_ponto(ponto)
        except ErroDeValidacao as erro:
            self._aviso("\n".join(f"✖ Ponto {ponto.ordem}: {m}" for m in erro.mensagens),
                        erro=True)
            return
        self.mostrar(self.plano_id)
        self.alterado.emit()
        self._aviso("✔ Plano salvo. Vale para as próximas calibrações.", certo=True)

    def remover_ponto(self) -> None:
        linha = self.tabela.currentRow()
        if linha < 0:
            self._aviso("Clique numa linha da tabela para escolher o ponto.")
            return
        ponto_id = self.tabela.item(linha, 0).data(Qt.UserRole)
        if ponto_id is None:  # ponto novo, ainda não salvo
            self.tabela.removeRow(linha)
            return
        try:
            self.repo.enviar_para_lixeira(Tipo.PONTO, ponto_id, None, datetime.datetime.now())
        except ErroDeValidacao as erro:
            self._aviso("\n".join(f"✖ {m}" for m in erro.mensagens), erro=True)
            return
        self.mostrar(self.plano_id)
        self.alterado.emit()
        self._aviso("✔ Ponto enviado para a Lixeira (pode ser restaurado de lá).", certo=True)

    def definir_edicao(self, pode: bool) -> None:
        """Modo consulta: sem botões e sem dar para digitar nas células."""
        self.pode_editar = pode
        for botao in (self.adicionar, self.remover, self.salvar):
            botao.setVisible(pode)
        self.tabela.setEditTriggers(self._gatilhos_edicao if pode
                                    else QAbstractItemView.NoEditTriggers)
        self.mostrar(self.plano_id)

    def _aviso(self, texto: str, erro: bool = False, certo: bool = False) -> None:
        cor = "#ef5350" if erro else "#43a047" if certo else "#ffd54f"
        self.avisos.setStyleSheet(f"color: {cor};")
        self.avisos.setText(texto)
