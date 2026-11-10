"""Janela de edição do instrumento (pedido do usuário em 2026-11-03).

A ficha da aba Instrumentos é só apresentação; para mudar, o botão EDITAR (ou Novo instrumento)
abre esta janela no meio da tela, deixando claro que ali se edita. Erros de digitação aparecem em
vermelho na área de avisos (sem pop-up); SALVAR grava e fecha.
"""

import datetime
import re

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
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from calibracao.dados.repositorio import (
    ErroDeValidacao,
    Instrumento,
    Plano,
    Repositorio,
    dividir_codigo,
)
from calibracao.interface.componentes import (
    BotaoCalendario,
    CampoComSugestoes,
    RotuloAviso,
    data_livre_para_banco,
    data_livre_para_tela,
    formatar_data,
    reais_em_texto,
)
from calibracao.interface.estilo import CORES
from calibracao.interface.painel_plano import numero
from calibracao.interface.tema_icones import por_icone
from calibracao.regras.localizacao import com_marcas, eh_indicativa, eh_reserva

DICA_CODIGO = ("Clique na setinha para escolher o tipo na lista (ex.: Paquímetro (PAQ)): o código "
               "já vem com o próximo número. Ou digite o código; ao escrever a sigla (ex.: PAQ-), "
               "aparece o próximo número e o Enter o completa.")
DICA_LOCAL = ("Comece a escrever e escolha um local da lista, para não criar o mesmo local com "
              "outro nome. Mais de um local: separe com / (ou clique em Mais um local). Local "
              "novo: é só escrever.")
_SIGLA_DIGITADA = re.compile(r"^\s*([A-Za-zÀ-ÿ]+)\s*(-\s*\d*)?\s*$")

DICA_PRIMEIRA = ("Quando fazer a primeira calibração no programa (olhe a próxima calibração na "
                 "planilha DQ05). Com ela o instrumento já entra no cronograma; depois da 1ª "
                 "calibração registrada, as datas seguintes vêm dela.")

# (campo, rótulo) na ordem da tela, em duas colunas.
ROTULOS = [("codigo", "Código"), ("tipo", "Tipo de instrumento"), ("localizacao", "Localização"),
           ("faixa", "Faixa de utilização"), ("resolucao", "Resolução"),
           ("fabricante", "Fabricante"),
           ("data_compra", "Data de compra"), ("periodicidade_meses", "Periodicidade (meses)"),
           ("custo_compra", "Custo de compra (R$)"), ("responsavel", "Responsável")]


def _mostrar(rotulo: QLabel, texto: str) -> None:
    """Dica/aviso embaixo do campo: só aparece (e ocupa lugar) quando tem texto."""
    rotulo.setText(texto)
    rotulo.setVisible(bool(texto))


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
        faixa.setStyleSheet(f"background: {CORES['aviso_fundo']}; color: #000000; padding: 6px; "
                            "font-weight: bold;")

        coluna = QVBoxLayout(self)
        coluna.addWidget(titulo)
        coluna.addWidget(faixa)
        coluna.addWidget(self._caixa_campos(), 1)
        self.avisos = RotuloAviso(wordWrap=True, objectName="avisos")
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
        # Código (pedido de 2026-11-10): lista "Paquímetro (PAQ)" com o próximo número, mas dá
        # para digitar; o campo de texto da lista é o campo do código.
        self.lista_codigo = QComboBox(editable=True)
        self.lista_codigo.setInsertPolicy(QComboBox.NoInsert)
        self.lista_codigo.setCompleter(None)  # digitar não completa com o nome do tipo
        self.lista_codigo.setMaxVisibleItems(15)
        self.lista_codigo.setToolTip(DICA_CODIGO)
        self.lista_codigo.activated.connect(self.escolher_sigla)
        self.campos["codigo"] = self.lista_codigo.lineEdit()
        self.campos["codigo"].setPlaceholderText(
            "Escolha o tipo na setinha ou digite (ex.: PAQ-019)")
        self.campos["codigo"].textChanged.connect(self._codigo_mudou)
        self.campos["codigo"].returnPressed.connect(self.usar_proximo_codigo)
        self.dica_codigo = RotuloAviso(objectName="dica", wordWrap=True)
        self._proximo_codigo: str | None = None
        self._codigos: dict[str, int] = {}
        # Tipo e localização com sugestões, como a pesquisa do Google (pedido de 2026-11-10).
        self.campos["tipo"] = CampoComSugestoes()
        self.campos["tipo"].setPlaceholderText("Comece a escrever e escolha na lista")
        self.campos["tipo"].setToolTip("Escolha um tipo da lista, para o mesmo tipo não aparecer "
                                       "com dois nomes. Tipo novo: é só escrever.")
        self.aviso_tipo = RotuloAviso(wordWrap=True)
        self.aviso_tipo.setStyleSheet(f"color: {CORES['aviso']};")
        self.campos["tipo"].textChanged.connect(
            lambda: _mostrar(self.aviso_tipo, self.campos["tipo"].aviso_de_novos("um tipo")))
        self.campos["localizacao"] = CampoComSugestoes(varios=True)
        self.campos["localizacao"].setPlaceholderText("Comece a escrever e escolha na lista")
        self.campos["localizacao"].setToolTip(DICA_LOCAL)
        self.mais_um_local = QPushButton("Mais um local")
        self.mais_um_local.setToolTip("Para instrumento usado em mais de um lugar: põe uma / e "
                                      "mostra os locais da lista.")
        self.mais_um_local.clicked.connect(self.campos["localizacao"].mais_um)
        por_icone(self.mais_um_local, "add_location_alt", CORES["titulo"])
        self.aviso_local = RotuloAviso(wordWrap=True)
        self.aviso_local.setStyleSheet(f"color: {CORES['aviso']};")
        self.campos["localizacao"].textChanged.connect(
            lambda: _mostrar(self.aviso_local,
                             self.campos["localizacao"].aviso_de_novos("um local")))
        for aviso in (self.dica_codigo, self.aviso_tipo, self.aviso_local):
            aviso.hide()  # só ocupa lugar quando tem o que dizer
        self.campos["periodicidade_meses"].setToolTip("De quantos em quantos meses calibrar.")
        self.campos["faixa"].setPlaceholderText("Adicione a unidade de medida (ex.: 0 a 150 mm)")
        self.campos["faixa"].setToolTip("Faixa em que o instrumento é usado, com a unidade de "
                                        "medida (ex.: 0 a 150 mm).")
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
        por_icone(self.novo_plano, "add", CORES["titulo"])

        self.campos["data_compra"].setPlaceholderText("dd/mm/aaaa")
        self.calendario_compra = BotaoCalendario(self.campos["data_compra"])
        data_compra = QHBoxLayout()
        data_compra.setContentsMargins(0, 0, 0, 0)
        data_compra.addWidget(self.campos["data_compra"], 1)
        data_compra.addWidget(self.calendario_compra)

        grade = QGridLayout()
        for indice, (nome, rotulo) in enumerate(ROTULOS):
            linha, coluna = divmod(indice, 2)
            grade.addWidget(QLabel(rotulo), linha, coluna * 2)
            if nome == "data_compra":
                grade.addLayout(data_compra, linha, coluna * 2 + 1)
            elif nome in ("codigo", "tipo", "localizacao"):
                grade.addLayout(self._com_aviso(nome), linha, coluna * 2 + 1)
            else:
                grade.addWidget(self.campos[nome], linha, coluna * 2 + 1)
        rotulo_primeira = QLabel("1ª calibração prevista")
        rotulo_primeira.setToolTip(DICA_PRIMEIRA)
        grade.addWidget(rotulo_primeira, 5, 0)
        self.calendario_primeira = BotaoCalendario(self.primeira)
        primeira = QHBoxLayout()
        primeira.setContentsMargins(0, 0, 0, 0)
        primeira.addWidget(self.primeira, 1)
        primeira.addWidget(self.calendario_primeira)
        grade.addLayout(primeira, 5, 1)
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

    def _com_aviso(self, nome: str) -> QVBoxLayout:
        """Campo com a linha de dica/aviso embaixo (código, tipo e localização)."""
        coluna = QVBoxLayout()
        coluna.setContentsMargins(0, 0, 0, 0)
        coluna.setSpacing(2)
        if nome == "codigo":
            coluna.addWidget(self.lista_codigo)
            coluna.addWidget(self.dica_codigo)
        elif nome == "tipo":
            coluna.addWidget(self.campos["tipo"])
            coluna.addWidget(self.aviso_tipo)
        else:
            linha = QHBoxLayout()
            linha.addWidget(self.campos["localizacao"], 1)
            linha.addWidget(self.mais_um_local)
            coluna.addLayout(linha)
            coluna.addWidget(self.aviso_local)
        return coluna

    def _recarregar_sugestoes(self) -> None:
        self.lista_codigo.blockSignals(True)
        self.lista_codigo.clear()
        for tipo, sigla in self.repo.siglas_dos_tipos():
            self.lista_codigo.addItem(f"{tipo} ({sigla})", (tipo, sigla))
        self.lista_codigo.setCurrentIndex(-1)
        self.lista_codigo.blockSignals(False)
        self.campos["tipo"].definir_opcoes(self.repo.tipos_cadastrados())
        self.campos["localizacao"].definir_opcoes(self.repo.locais_cadastrados())
        self._codigos = {i.codigo.casefold(): i.id
                         for i in self.repo.listar_instrumentos(incluir_desativados=True)}

    def _recarregar_planos(self) -> None:
        self.plano.clear()
        self.plano.addItem("— sem plano —", None)
        for plano in self.repo.listar_planos():
            self.plano.addItem(plano.nome, plano.id)

    def _preencher(self) -> None:
        self._recarregar_sugestoes()
        self._recarregar_planos()
        dados = self.instrumento or Instrumento(codigo="", tipo="")
        for nome, campo in self.campos.items():
            valor = getattr(dados, nome)
            campo.setText(self._para_tela(nome, valor))
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
        self.calendario_primeira.setEnabled(not ja_calibrado)
        self.dica_primeira.setText("Não é mais usada: já há calibração no programa"
                                   if ja_calibrado
                                   else "Só até a 1ª calibração registrada no programa")
        self.observacoes.setText(dados.observacoes or "")

    # --- Ações ------------------------------------------------------------------------------

    def escolher_sigla(self, indice: int) -> None:
        """Escolheu "Paquímetro (PAQ)" na lista: código com o próximo número e o tipo."""
        tipo, sigla = self.lista_codigo.itemData(indice)
        self.campos["codigo"].setText(self.repo.proximo_codigo(sigla) or f"{sigla}-")
        self.campos["tipo"].setText(tipo)

    def _codigo_mudou(self, texto: str) -> None:
        """Ao escrever a sigla (PAQ ou PAQ-0), mostra o próximo número; código repetido em
        vermelho."""
        self._proximo_codigo = None
        self.dica_codigo.setStyleSheet("")
        _mostrar(self.dica_codigo, "")
        digitado = texto.strip()
        dono = self._codigos.get(digitado.casefold())
        if dono is not None and (self.instrumento is None or dono != self.instrumento.id):
            self.dica_codigo.setStyleSheet(f"color: {CORES['erro']};")
            _mostrar(self.dica_codigo, f"✖ Já existe um instrumento {digitado}.")
            return
        achado = _SIGLA_DIGITADA.match(texto)
        if not achado or (self.instrumento and digitado == self.instrumento.codigo):
            return
        sigla = achado.group(1).upper()
        proximo = self.repo.proximo_codigo(sigla)
        if proximo is None:
            return
        compacto = digitado.upper().replace(" ", "")
        if compacto == proximo:
            _mostrar(self.dica_codigo, f"{proximo} é o próximo número livre de {sigla}.")
        elif dividir_codigo(texto) is None or proximo.startswith(compacto):
            self._proximo_codigo = proximo
            _mostrar(self.dica_codigo, f"Próximo número de {sigla}: {proximo} — aperte "
                                       "Enter para usar (ou continue digitando outro).")

    def usar_proximo_codigo(self) -> None:
        """Enter no código: completa com o próximo número sugerido (se houver sugestão)."""
        if self._proximo_codigo:
            self.campos["codigo"].setText(self._proximo_codigo)

    def nomes_novos(self) -> list[str]:
        """Tipo e locais digitados que nenhum instrumento usa (com o que é cada um)."""
        return ([f'tipo "{n}"' for n in self.campos["tipo"].nomes_novos()]
                + [f'local "{n}"' for n in self.campos["localizacao"].nomes_novos()])

    def confirmar_nomes_novos(self, novos: list[str]) -> bool:
        """Pergunta antes de criar tipo ou local novo (evita o mesmo nome escrito de outro
        jeito). True = criar."""
        lista = "\n".join(f"• {n}" for n in novos)
        caixa = QMessageBox(QMessageBox.Warning, "Nome novo",
                            f"Nenhum instrumento usa ainda:\n\n{lista}\n\nSe já existe na lista "
                            "com outro jeito de escrever, volte e escolha da lista. É mesmo novo?",
                            parent=self)
        criar = caixa.addButton("Criar novo", QMessageBox.AcceptRole)
        voltar = caixa.addButton("Voltar e escolher da lista", QMessageBox.RejectRole)
        caixa.setDefaultButton(voltar)
        caixa.exec()
        return caixa.clickedButton() is criar

    def _marca_clicada(self, reserva: bool | None = None,
                       indicativa: bool | None = None) -> None:
        campo = self.campos["localizacao"]
        campo.setText(com_marcas(campo.text(), reserva, indicativa) or "")
        campo.setCursorPosition(0)

    def _localizacao_mudou(self, texto: str) -> None:
        self.reserva.setChecked(eh_reserva(texto))
        self.indicativa.setChecked(eh_indicativa(texto))

    @staticmethod
    def _para_tela(nome: str, valor) -> str:
        if nome == "custo_compra":
            return reais_em_texto(valor)
        if nome == "data_compra":
            return data_livre_para_tela(valor)
        return "" if valor is None else str(valor)

    def tem_alteracao(self) -> bool:
        """Algo digitado e ainda não salvo."""
        dados = self.instrumento or Instrumento(codigo="", tipo="")
        for nome, campo in self.campos.items():
            valor = getattr(dados, nome)
            if campo.text().strip() != self._para_tela(nome, valor).strip():
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
        novos = self.nomes_novos()
        if novos and not self.confirmar_nomes_novos(novos):
            self._aviso("Escolha o tipo e a localização na lista de sugestões (comece a "
                        "escrever no campo).")
            return
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
            data_compra=data_livre_para_banco(self.campos["data_compra"].text()),
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
