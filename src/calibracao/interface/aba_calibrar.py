"""Aba Calibrar (pedido do usuário em 2026-11-03): onde se faz a calibração.

À esquerda a mesma lista de instrumentos da aba Instrumentos; à direita, os dados do instrumento
escolhido (só apresentação), o botão NOVA CALIBRAÇÃO e as calibrações já feitas — clicar numa
delas abre a calibração só para ver, com o botão EDITAR para corrigir.
"""

import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import QGridLayout, QGroupBox, QHBoxLayout, QLabel, QVBoxLayout, QWidget

from calibracao.dados.repositorio import Instrumento, Repositorio
from calibracao.interface.aba_calibracoes import PainelCalibracoes
from calibracao.interface.componentes import formatar_data
from calibracao.interface.estilo import CORES_SITUACAO, destacar, tem_destaque
from calibracao.interface.lista_instrumentos import ListaInstrumentos
from calibracao.regras.condicao import so_qualitativos
from calibracao.regras.lixeira import Tipo

# (chave, rótulo) dos dados mostrados do instrumento escolhido, em duas colunas.
DADOS = [("codigo", "Código"), ("tipo", "Tipo de instrumento"), ("localizacao", "Localização"),
         ("condicao", "Condição"), ("plano", "Plano"), ("periodicidade", "Periodicidade"),
         ("proxima", "Próxima calibração"), ("situacao", "Situação")]


class AbaCalibrar(QWidget):
    alterado = Signal()  # calibração registrada, corrigida ou na Lixeira

    def __init__(self, repositorio: Repositorio, hoje: datetime.date) -> None:
        super().__init__()
        self.repo = repositorio
        self.hoje = hoje
        self.atual: Instrumento | None = None
        self.situacoes: dict = {}

        self.lista = ListaInstrumentos()
        self.lista.escolhido.connect(
            lambda instrumento_id: self.mostrar(self.repo.obter_instrumento(instrumento_id)))
        self.painel_calibracoes = PainelCalibracoes(repositorio, hoje)
        self.painel_calibracoes.alterado.connect(self._calibracoes_mudaram)

        self.valores = {chave: QLabel(textFormat=Qt.RichText) for chave, _ in DADOS}
        grade = QGridLayout()
        for indice, (chave, rotulo) in enumerate(DADOS):
            linha, coluna = divmod(indice, 2)
            grade.addWidget(QLabel(f"{rotulo}:"), linha, coluna * 2)
            grade.addWidget(self.valores[chave], linha, coluna * 2 + 1)
            grade.setColumnStretch(coluna * 2 + 1, 1)
        self.aviso_trena = QLabel(objectName="dica", wordWrap=True)
        caixa_instrumento = QGroupBox("Instrumento escolhido")
        coluna_instrumento = QVBoxLayout(caixa_instrumento)
        coluna_instrumento.addWidget(QLabel(
            "Só para ver. Para mudar os dados do instrumento ou o plano, use a aba Instrumentos.",
            objectName="dica"))
        coluna_instrumento.addLayout(grade)
        coluna_instrumento.addWidget(self.aviso_trena)

        self.caixa_calibracoes = QGroupBox("Calibrações")
        QVBoxLayout(self.caixa_calibracoes).addWidget(self.painel_calibracoes)

        direita = QVBoxLayout()
        direita.setContentsMargins(0, 0, 0, 0)
        direita.addWidget(caixa_instrumento)
        direita.addWidget(self.caixa_calibracoes, 1)
        coluna_direita = QWidget()
        coluna_direita.setLayout(direita)

        faixa = QHBoxLayout(self)
        faixa.addWidget(self.lista, 1)
        faixa.addWidget(coluna_direita, 1)
        self.mostrar(None)

    def atualizar(self, situacoes: dict) -> None:
        """Recarrega a lista (a janela já calculou o cronograma) e o instrumento aberto."""
        self.situacoes = situacoes
        self.lista.atualizar(self.repo.listar_instrumentos(incluir_desativados=True),
                             self.repo.condicoes_atuais(), situacoes)
        self.recarregar_atual()

    def recarregar_atual(self) -> None:
        if self.atual is None:
            return
        if self.repo.na_lixeira(Tipo.INSTRUMENTO, self.atual.id):
            self.mostrar(None)
        else:
            self.mostrar(self.repo.obter_instrumento(self.atual.id))

    def mostrar(self, instrumento: Instrumento | None) -> None:
        self.atual = instrumento
        self.lista.marcar(instrumento.id if instrumento else None)
        self.painel_calibracoes.mostrar(instrumento)
        if instrumento is None:
            for valor in self.valores.values():
                valor.setText("—")
            self.caixa_calibracoes.setTitle("Calibrações")
            self.aviso_trena.setText("")
            return
        plano = self.repo.obter_plano(instrumento.plano_id).nome if instrumento.plano_id \
            else "sem plano"
        situacao = self.situacoes.get(instrumento.id)
        local = instrumento.localizacao or "—"
        textos = {
            "codigo": instrumento.codigo, "tipo": instrumento.tipo,
            "localizacao": destacar(local) if tem_destaque(local) else local,
            "condicao": self.repo.condicao_atual(instrumento.id).condicao.value,
            "plano": plano,
            "periodicidade": (f"{instrumento.periodicidade_meses} meses"
                              if instrumento.periodicidade_meses else "—"),
            "proxima": formatar_data(self.repo.prevista_atual(instrumento.id)),
            "situacao": situacao.value if situacao else "—",
        }
        for chave, texto in textos.items():
            self.valores[chave].setText(f"<b>{texto}</b>")
        cores = CORES_SITUACAO.get(situacao) if situacao else None
        self.valores["situacao"].setStyleSheet(
            f"background: {cores[0]}; color: {cores[1]}; padding: 2px 6px;" if cores else "")
        self.caixa_calibracoes.setTitle(f"Calibrações — {instrumento.codigo}")
        self.aviso_trena.setText(
            "Trena com orientação indicativa: a calibração tem só os pontos qualitativos."
            if so_qualitativos(instrumento.tipo, instrumento.localizacao) else "")

    def _calibracoes_mudaram(self) -> None:
        self.alterado.emit()  # a janela recalcula o cronograma e chama atualizar()

    def definir_edicao(self, pode: bool) -> None:
        self.painel_calibracoes.definir_edicao(pode)
