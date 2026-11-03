"""Janela de edição do instrumento (pedido do usuário em 2026-11-03).

A ficha da aba Instrumentos é só apresentação; para mudar, o botão EDITAR (ou Novo instrumento)
abre esta janela no meio da tela, deixando claro que ali se edita. Erros de digitação aparecem em
vermelho na área de avisos (sem pop-up); SALVAR grava e fecha.
"""

import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QCheckBox,
    QComboBox,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QPushButton,
    QVBoxLayout,
)

from calibracao.dados.repositorio import ErroDeValidacao, Instrumento, Plano, Repositorio
from calibracao.interface.componentes import formatar_data
from calibracao.interface.estilo import CORES
from calibracao.interface.painel_plano import numero, numero_em_texto
from calibracao.regras.localizacao import com_marcas, eh_indicativa, eh_reserva

DICA_PRIMEIRA = ("Quando fazer a primeira calibração no programa (olhe a próxima calibração na "
                 "planilha DQ05). Com ela o instrumento já entra no cronograma; depois da 1ª "
                 "calibração registrada, as datas seguintes vêm dela.")

# (campo, rótulo) na ordem da tela, em duas colunas.
ROTULOS = [("codigo", "Código"), ("tipo", "Tipo"), ("localizacao", "Localização"),
           ("faixa", "Faixa"), ("resolucao", "Resolução"), ("fabricante", "Fabricante"),
           ("data_compra", "Data de compra"), ("periodicidade_meses", "Periodicidade (meses)"),
           ("custo_compra", "Custo de compra (R$)"), ("responsavel", "Responsável")]


def _texto(campo: QLineEdit) -> str | None:
    return campo.text().strip() or None


def _data_digitada(texto: str) -> datetime.date | None:
    """dd/mm/aaaa (vazio = None); ValueError se não for uma data."""
    texto = texto.strip()
    return datetime.datetime.strptime(texto, "%d/%m/%Y").date() if texto else None


class JanelaEditarInstrumento(QDialog):
    salvo = Signal(int)  # id do instrumento gravado

    def __init__(self, repositorio: Repositorio, hoje: datetime.date,
                 instrumento: Instrumento | None, parent=None) -> None:
        super().__init__(parent)
        self.repo = repositorio
        self.hoje = hoje
        self.instrumento = instrumento
        codigo = instrumento.codigo if instrumento else ""
        self.setWindowTitle(f"Editar instrumento — {codigo}" if instrumento
                            else "Novo instrumento")
        self.setMinimumSize(1300, 720)

        titulo = QLabel(f"EDITAR INSTRUMENTO — {codigo}" if instrumento
                        else "NOVO INSTRUMENTO", objectName="titulo", alignment=Qt.AlignCenter)
        faixa = QLabel("Você está editando: mude o que precisar e clique em SALVAR "
                       "(ou em Cancelar para desistir).", alignment=Qt.AlignCenter)
        faixa.setStyleSheet(f"background: {CORES['aviso']}; color: #000000; padding: 6px; "
                            "font-weight: bold;")

        coluna = QVBoxLayout(self)
        coluna.addWidget(titulo)
        coluna.addWidget(faixa)
        coluna.addWidget(self._caixa_campos(), 1)
        self.avisos = QLabel(wordWrap=True, objectName="avisos")
        coluna.addWidget(self.avisos)
        self.cancelar = QPushButton("Cancelar")
        self.cancelar.clicked.connect(self.reject)
        self.salvar = QPushButton("SALVAR", objectName="principal")
        self.salvar.clicked.connect(self.salvar_instrumento)
        botoes = QHBoxLayout()
        botoes.addStretch(1)
        botoes.addWidget(self.cancelar, 1)
        botoes.addWidget(self.salvar, 2)
        coluna.addLayout(botoes)
        self._preencher()

    # --- Montagem ---------------------------------------------------------------------------

    def _caixa_campos(self) -> QGroupBox:
        self.campos = {nome: QLineEdit() for nome, _ in ROTULOS}
        self.campos["periodicidade_meses"].setToolTip("De quantos em quantos meses calibrar.")
        self.campos["custo_compra"].setToolTip("Valor pago na compra, em reais (ex.: 350,00).")
        self.plano = QComboBox()
        self.exige = QCheckBox("Precisa de calibração")
        self.exige.setToolTip("Desmarque para instrumentos que não precisam de calibração: "
                              "eles saem do cronograma.")
        self.observacoes = QLineEdit()
        # 1ª calibração prevista (pedido de 2026-11-03): no lugar do histórico da DQ05.
        self.primeira = QLineEdit(placeholderText="dd/mm/aaaa")
        self.primeira.setToolTip(DICA_PRIMEIRA)
        self.dica_primeira = QLabel(objectName="dica")
        self.dica_primeira.setToolTip(DICA_PRIMEIRA)
        # Caixas "Reserva" e "Orientação indicativa": põem/tiram a marca na localização;
        # digitar à mão também marca a caixa.
        self.reserva = QCheckBox("Reserva")
        self.reserva.setToolTip("Marque se o instrumento está guardado como reserva: a "
                                "localização ganha \"- Reserva\" (em azul). Desmarque quando "
                                "ele voltar a ser usado.")
        self.reserva.clicked.connect(lambda marcada: self._marca_clicada(reserva=marcada))
        self.indicativa = QCheckBox("Orientação indicativa")
        self.indicativa.setToolTip("Marque se o instrumento é usado como orientação indicativa "
                                   "(continua em uso e no cronograma): a localização ganha "
                                   "\"- Orientação indicativa\". Fica no histórico ao salvar.")
        self.indicativa.clicked.connect(
            lambda marcada: self._marca_clicada(indicativa=marcada))
        self.campos["localizacao"].textChanged.connect(self._localizacao_mudou)
        self.novo_plano = QPushButton("Novo plano")
        self.novo_plano.setToolTip("Cria um plano vazio; depois de salvar, inclua os pontos em "
                                   "Plano de calibração.")
        self.novo_plano.clicked.connect(self.pedir_nome_do_plano)

        grade = QGridLayout()
        for indice, (nome, rotulo) in enumerate(ROTULOS):
            linha, coluna = divmod(indice, 2)
            grade.addWidget(QLabel(rotulo), linha, coluna * 2)
            grade.addWidget(self.campos[nome], linha, coluna * 2 + 1)
        rotulo_primeira = QLabel("1ª calibração prevista")
        rotulo_primeira.setToolTip(DICA_PRIMEIRA)
        grade.addWidget(rotulo_primeira, 5, 0)
        grade.addWidget(self.primeira, 5, 1)
        grade.addWidget(self.dica_primeira, 5, 2, 1, 2)
        grade.addWidget(QLabel("Plano"), 6, 0)
        grade.addWidget(self.plano, 6, 1, 1, 2)
        grade.addWidget(self.novo_plano, 6, 3)
        grade.addWidget(QLabel("Observações"), 7, 0)
        grade.addWidget(self.observacoes, 7, 1, 1, 3)
        caixas = QHBoxLayout()
        for caixa in (self.exige, self.reserva, self.indicativa):
            caixas.addWidget(caixa)
            caixas.addSpacing(30)
        caixas.addStretch(1)
        grade.addLayout(caixas, 8, 1, 1, 3)
        grade.setColumnStretch(1, 1)
        grade.setColumnStretch(3, 1)
        grade.setVerticalSpacing(12)
        caixa = QGroupBox("Dados do instrumento")
        QVBoxLayout(caixa).addLayout(grade)
        return caixa

    def _recarregar_planos(self) -> None:
        self.plano.clear()
        self.plano.addItem("— sem plano —", None)
        for plano in self.repo.listar_planos():
            self.plano.addItem(plano.nome, plano.id)

    def _preencher(self) -> None:
        self._recarregar_planos()
        dados = self.instrumento or Instrumento(codigo="", tipo="")
        for nome, campo in self.campos.items():
            valor = getattr(dados, nome)
            campo.setText(numero_em_texto(valor) if nome == "custo_compra"
                          else "" if valor is None else str(valor))
            campo.setCursorPosition(0)  # texto longo mostra o começo, não o fim
        if dados.plano_id is not None and self.plano.findData(dados.plano_id) < 0:
            # plano na Lixeira: continua aparecendo, para não sumir sem ninguém perceber
            nome = self.repo.obter_plano(dados.plano_id).nome
            self.plano.addItem(f"{nome} (na Lixeira)", dados.plano_id)
        self.plano.setCurrentIndex(max(self.plano.findData(dados.plano_id), 0))
        self.exige.setChecked(dados.exige_calibracao)
        self.primeira.setText(formatar_data(dados.primeira_prevista)
                              if dados.primeira_prevista else "")
        # Depois da 1ª calibração registrada, a data não é mais usada: fica só para consulta.
        ja_calibrado = bool(self.instrumento and self.repo.listar_calibracoes(self.instrumento.id))
        self.primeira.setReadOnly(ja_calibrado)
        self.dica_primeira.setText("Não é mais usada: já há calibração no programa"
                                   if ja_calibrado
                                   else "Só até a 1ª calibração registrada no programa")
        self.observacoes.setText(dados.observacoes or "")

    # --- Ações ------------------------------------------------------------------------------

    def _marca_clicada(self, reserva: bool | None = None,
                       indicativa: bool | None = None) -> None:
        campo = self.campos["localizacao"]
        campo.setText(com_marcas(campo.text(), reserva, indicativa) or "")
        campo.setCursorPosition(0)

    def _localizacao_mudou(self, texto: str) -> None:
        self.reserva.setChecked(eh_reserva(texto))
        self.indicativa.setChecked(eh_indicativa(texto))

    def tem_alteracao(self) -> bool:
        """Algo digitado e ainda não salvo."""
        dados = self.instrumento or Instrumento(codigo="", tipo="")
        for nome, campo in self.campos.items():
            valor = getattr(dados, nome)
            salvo = (numero_em_texto(valor) if nome == "custo_compra"
                     else "" if valor is None else str(valor))
            if campo.text().strip() != salvo.strip():
                return True
        primeira = formatar_data(dados.primeira_prevista) if dados.primeira_prevista else ""
        return (self.primeira.text().strip() != primeira
                or self.observacoes.text().strip() != (dados.observacoes or "").strip()
                or self.plano.currentData() != dados.plano_id
                or self.exige.isChecked() != dados.exige_calibracao)

    def pedir_nome_do_plano(self) -> None:
        codigo = self.campos["codigo"].text().strip()
        nome, ok = QInputDialog.getText(self, "Novo plano", "Nome do plano:",
                                        text=f"Plano {codigo}" if codigo else "Plano ")
        if ok:
            self.criar_plano(nome)

    def criar_plano(self, nome: str) -> None:
        """Cria o plano e já o escolhe no campo Plano (falta clicar em SALVAR para ligar)."""
        try:
            plano_id = self.repo.incluir_plano(Plano(nome))
        except ErroDeValidacao as erro:
            self._aviso("\n".join(f"✖ {m}" for m in erro.mensagens), erro=True)
            return
        self._recarregar_planos()
        self.plano.setCurrentIndex(self.plano.findData(plano_id))
        self._aviso(f"Plano \"{nome.strip()}\" criado. Clique em SALVAR para ligá-lo a este "
                    "instrumento; depois inclua os pontos em Plano de calibração.")

    def salvar_instrumento(self) -> None:
        texto_meses = self.campos["periodicidade_meses"].text().strip()
        if texto_meses and not texto_meses.isdigit():
            self._aviso("✖ A periodicidade deve ser um número inteiro de meses.", erro=True)
            return
        try:
            custo = numero(self.campos["custo_compra"].text().replace("R$", ""))
        except ValueError:
            self._aviso("✖ O custo de compra deve ser um número (ex.: 350,00).", erro=True)
            return
        try:
            primeira = _data_digitada(self.primeira.text())
        except ValueError:
            self._aviso("✖ A 1ª calibração prevista deve ser uma data (dd/mm/aaaa).", erro=True)
            return
        instrumento = Instrumento(
            codigo=self.campos["codigo"].text().strip(),
            tipo=self.campos["tipo"].text().strip(),
            localizacao=_texto(self.campos["localizacao"]),
            faixa=_texto(self.campos["faixa"]),
            resolucao=_texto(self.campos["resolucao"]),
            fabricante=_texto(self.campos["fabricante"]),
            data_compra=_texto(self.campos["data_compra"]),
            periodicidade_meses=int(texto_meses) if texto_meses else None,
            plano_id=self.plano.currentData(),
            exige_calibracao=self.exige.isChecked(),
            observacoes=_texto(self.observacoes),
            custo_compra=custo,
            responsavel=_texto(self.campos["responsavel"]),
            primeira_prevista=primeira,
            id=self.instrumento.id if self.instrumento else None,
        )
        try:
            if instrumento.id is None:
                instrumento.id = self.repo.incluir_instrumento(instrumento, self.hoje)
            else:
                self.repo.atualizar_instrumento(instrumento, self.hoje)
        except ErroDeValidacao as erro:
            self._aviso("\n".join(f"✖ {m}" for m in erro.mensagens), erro=True)
            return
        self.instrumento = self.repo.obter_instrumento(instrumento.id)
        self.salvo.emit(instrumento.id)
        self.accept()

    def _aviso(self, texto: str, erro: bool = False) -> None:
        self.avisos.setStyleSheet(f"color: {CORES['erro'] if erro else CORES['aviso']};")
        self.avisos.setText(texto)
