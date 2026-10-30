"""Sub-aba Calibrações do instrumento: histórico, registro de calibração e gráfico de tendência.

Registrar abre uma janela maximizada com os pontos do plano: o resultado de cada ponto aparece
enquanto se digita (verde/vermelho/amarelo) e, no fim, quem analisa escolhe o parecer final —
que muda a condição do instrumento (ver `calibracao.regras.condicao`). A mesma janela corrige uma
calibração salva (tudo menos a data); cada correção fica registrada e aparece em "Ver pontos…".
"""

import datetime
import getpass
import platform

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QHeaderView,
    QLabel,
    QLineEdit,
    QPushButton,
    QTableWidget,
    QTableWidgetItem,
    QVBoxLayout,
    QWidget,
)

from calibracao.dados.repositorio import (
    Calibracao,
    CorrecaoCalibracao,
    ErroDeValidacao,
    Instrumento,
    NovaCalibracao,
    PontoMedido,
    PontoPlano,
    PontoRegistrado,
    Repositorio,
)
from calibracao.interface.componentes import (
    aplicar_destaques,
    celula,
    formatar_data,
    tabela_somente_leitura,
)
from calibracao.interface.estilo import CORES, CORES_PARECER, CORES_RESULTADO
from calibracao.interface.painel_plano import numero, numero_em_texto
from calibracao.regras.avaliacao import Resultado, resultado_geral
from calibracao.regras.condicao import pareceres_permitidos
from calibracao.regras.lixeira import Tipo

DICA_U = ("Incerteza expandida de medição (U), do certificado: quanto o resultado pode variar "
          "para mais ou para menos. Já vem a do plano; troque se o certificado trouxer outra.")
DICA_SEM_NOMINAL = ("Ponto sem nominal fixo (ex.: durômetro, laboratório externo): digite o "
                    "ERRO que está no certificado.")
NUMERICOS = ("NUMERICO", "LIMITE")
ESCOLHAS = {"— escolha —": None, "Aprovado": Resultado.APROVADO,
            "Reprovado": Resultado.REPROVADO}


def dinheiro(valor: float | None) -> str:
    if valor is None:
        return "—"
    return f"R$ {valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")


def referencia(ponto) -> str:
    """O que o ponto exige, em texto (serve para o ponto do plano e para o registrado)."""
    unidade = f" {ponto.unidade}" if ponto.unidade else ""
    if ponto.tipo == "NUMERICO":
        inferior, superior = ponto.tolerancia_inferior, ponto.tolerancia_superior
        if inferior is not None and superior is not None and abs(inferior + superior) < 1e-12:
            tolerancia = f"± {numero_em_texto(superior)}"
        elif inferior is None and superior is None:
            tolerancia = "sem tolerância"
        else:
            tolerancia = (f"{numero_em_texto(inferior) or '—'} a "
                          f"{numero_em_texto(superior) or '—'}")
        if ponto.valor_nominal is None:
            return f"Erro dentro de {tolerancia}{unidade} (sem nominal fixo)"
        return f"{numero_em_texto(ponto.valor_nominal)}{unidade}, tolerância {tolerancia}"
    if ponto.tipo == "LIMITE":
        partes = []
        if ponto.valor_minimo is not None:
            partes.append(f"mín. {numero_em_texto(ponto.valor_minimo)}")
        if ponto.valor_maximo is not None:
            partes.append(f"máx. {numero_em_texto(ponto.valor_maximo)}")
        return (" e ".join(partes) or "sem limite") + unidade
    if ponto.tipo == "CLASSE":
        return f"Classe exigida: {ponto.classe_exigida or '—'}"
    if ponto.tipo == "CRITERIO":
        return ponto.criterio or "Critério"
    return "Verificação visual"


def celula_resultado(resultado: Resultado, motivo: str | None = None) -> QTableWidgetItem:
    texto = f"{resultado.value} — {motivo}" if motivo else resultado.value
    return celula(texto, CORES_RESULTADO[resultado])


def _maximizar(janela: QDialog) -> None:
    janela.setWindowFlags(janela.windowFlags() | Qt.WindowMaximizeButtonHint)
    janela.setWindowState(Qt.WindowMaximized)


class JanelaNovaCalibracao(QDialog):
    """Registrar calibração: dados do certificado, pontos medidos e parecer final.

    Com `corrigir`, a janela vem preenchida com a calibração salva para corrigir; os pontos são os
    da "foto" guardada com ela (não os do plano atual) e a data não muda.
    """

    # Colunas da tabela de pontos
    (NUM, SECAO, DESCRICAO, REFERENCIA, MEDIDO, INCERTEZA, PADRAO, INDICACAO, NAO_APLICAVEL,
     OBSERVACAO, RESULTADO) = range(11)

    def __init__(self, repositorio: Repositorio, instrumento: Instrumento, hoje: datetime.date,
                 parent=None, corrigir: Calibracao | None = None, usuario: str = "") -> None:
        super().__init__(parent)
        self.repo = repositorio
        self.instrumento = instrumento
        self.hoje = hoje
        self.corrigindo = corrigir
        self.usuario = usuario
        self.calibracao_id: int | None = corrigir.id if corrigir else None
        self.mudancas: list[str] = []
        self.pontos: list[PontoPlano] | list[PontoRegistrado] = (
            repositorio.pontos_da_calibracao(corrigir.id) if corrigir
            else repositorio.listar_pontos(instrumento.plano_id))
        acao = "Corrigir" if corrigir else "Registrar"
        self.setWindowTitle(f"{acao} calibração — {instrumento.codigo}")
        _maximizar(self)

        texto = f"{acao.upper()} CALIBRAÇÃO — {instrumento.codigo} ({instrumento.tipo})"
        if corrigir:
            texto += f" DE {formatar_data(corrigir.data_calibracao)}"
        titulo = QLabel(texto, objectName="titulo", alignment=Qt.AlignCenter)
        coluna = QVBoxLayout(self)
        coluna.addWidget(titulo)
        coluna.addWidget(self._caixa_dados())
        coluna.addWidget(self._caixa_pontos(), 1)
        coluna.addWidget(self._caixa_parecer())
        self._atualizar_geral()
        if corrigir:
            self._preencher_com(corrigir)

    # --- Montagem ---------------------------------------------------------------------------

    def _caixa_dados(self) -> QGroupBox:
        self.data = QDateEdit(QDate(self.hoje.year, self.hoje.month, self.hoje.day),
                              calendarPopup=True)
        self.data.setDisplayFormat("dd/MM/yyyy")
        self.data.setMaximumDate(QDate(self.hoje.year, self.hoje.month, self.hoje.day))
        self.data.setToolTip("Data em que a calibração foi feita (a do certificado).")
        self.laboratorio = QLineEdit()
        self.certificado = QLineEdit()
        self.responsavel = QLineEdit()
        self.custo = QLineEdit(placeholderText="ex.: 150,00")
        self.observacoes = QLineEdit()
        campos = [("Data da calibração", self.data), ("Laboratório", self.laboratorio),
                  ("Certificado", self.certificado), ("Responsável", self.responsavel),
                  ("Custo (R$)", self.custo), ("Observações", self.observacoes)]
        grade = QGridLayout()
        for indice, (rotulo, campo) in enumerate(campos):
            linha, coluna = divmod(indice, 3)
            grade.addWidget(QLabel(rotulo), linha, coluna * 2)
            grade.addWidget(campo, linha, coluna * 2 + 1)
            grade.setColumnStretch(coluna * 2 + 1, 1)
        caixa = QGroupBox("Dados da calibração")
        caixa.setLayout(grade)
        return caixa

    def _caixa_pontos(self) -> QGroupBox:
        colunas = [
            ("Nº", ""), ("Seção", ""), ("Descrição", ""), ("Exigido", "O que o ponto exige."),
            ("Medido (ou erro)", "Valor medido. Em ponto sem nominal fixo, o erro do "
                                 "certificado. Em ponto de verificação, escolha o resultado."),
            ("Incerteza (U)", DICA_U),
            ("Padrão", "Só registro, quando o certificado traz (pontos sem nominal fixo)."),
            ("Indicação", "Só registro, quando o certificado traz (pontos sem nominal fixo)."),
            ("Não aplicável", "Marque se o ponto não se aplica nesta calibração (exige "
                              "observação); ele não conta no resultado."),
            ("Observação", "Obrigatória quando o ponto é marcado como não aplicável."),
            ("Resultado", "Calculado na hora, sempre considerando a Incerteza (U)."),
        ]
        self.tabela = QTableWidget(len(self.pontos), len(colunas))
        self.tabela.verticalHeader().setVisible(False)
        for indice, (texto, dica) in enumerate(colunas):
            item = QTableWidgetItem(texto)
            item.setToolTip(dica)
            self.tabela.setHorizontalHeaderItem(indice, item)
        cabecalho = self.tabela.horizontalHeader()
        cabecalho.setSectionResizeMode(QHeaderView.ResizeToContents)
        cabecalho.setSectionResizeMode(self.REFERENCIA, QHeaderView.Stretch)
        cabecalho.setSectionResizeMode(self.OBSERVACAO, QHeaderView.Stretch)
        self.tabela.setSelectionMode(QAbstractItemView.NoSelection)

        self.tabela.blockSignals(True)
        for linha, ponto in enumerate(self.pontos):
            self._montar_linha(linha, ponto)
        self.tabela.blockSignals(False)
        self.tabela.itemChanged.connect(self._mudou_celula)
        for linha in range(len(self.pontos)):
            self._avaliar_linha(linha)

        sem_nominal = sum(1 for p in self.pontos if p.tipo == "NUMERICO"
                          and p.valor_nominal is None)
        dica = ("Preencha todos os pontos: ponto em branco não deixa salvar. Clique duas vezes "
                "numa célula para digitar.")
        if sem_nominal:
            dica += f" {sem_nominal} ponto(s) sem nominal fixo: digite o ERRO do certificado."
        origem = "registrados" if self.corrigindo else "do plano"
        caixa = QGroupBox(f"Pontos {origem} — {len(self.pontos)}")
        coluna = QVBoxLayout(caixa)
        coluna.addWidget(QLabel(dica, objectName="dica", wordWrap=True))
        coluna.addWidget(self.tabela)
        return caixa

    def _fixo(self, linha: int, coluna: int, texto: str) -> None:
        item = celula(texto)
        item.setFlags(Qt.ItemIsEnabled)
        self.tabela.setItem(linha, coluna, item)

    def _editavel(self, linha: int, coluna: int, texto: str = "") -> None:
        self.tabela.setItem(linha, coluna, QTableWidgetItem(texto))

    def _montar_linha(self, linha: int, ponto: PontoPlano | PontoRegistrado) -> None:
        self._fixo(linha, self.NUM, str(ponto.ordem))
        self._fixo(linha, self.SECAO, ponto.secao or "")
        self._fixo(linha, self.DESCRICAO, ponto.descricao)
        self._fixo(linha, self.REFERENCIA, referencia(ponto))
        if ponto.tipo in NUMERICOS:
            self._editavel(linha, self.MEDIDO)
            self._editavel(linha, self.INCERTEZA, numero_em_texto(ponto.incerteza))
            if ponto.tipo == "NUMERICO" and ponto.valor_nominal is None:
                self.tabela.item(linha, self.MEDIDO).setToolTip(DICA_SEM_NOMINAL)
                self._editavel(linha, self.PADRAO)
                self._editavel(linha, self.INDICACAO)
            else:
                self._fixo(linha, self.PADRAO, "—")
                self._fixo(linha, self.INDICACAO, "—")
        else:
            escolha = QComboBox()
            escolha.addItems(ESCOLHAS)
            escolha.currentIndexChanged.connect(lambda _, n=linha: self._avaliar_linha(n))
            self.tabela.setCellWidget(linha, self.MEDIDO, escolha)
            for coluna in (self.INCERTEZA, self.PADRAO, self.INDICACAO):
                self._fixo(linha, coluna, "—")
        nao_aplicavel = QTableWidgetItem()
        nao_aplicavel.setFlags(Qt.ItemIsEnabled | Qt.ItemIsUserCheckable)
        nao_aplicavel.setCheckState(Qt.Unchecked)
        self.tabela.setItem(linha, self.NAO_APLICAVEL, nao_aplicavel)
        self._editavel(linha, self.OBSERVACAO)
        self._fixo(linha, self.RESULTADO, "")

    def _caixa_parecer(self) -> QGroupBox:
        self.geral = QLabel()
        self.parecer = QComboBox()
        self.parecer.setToolTip("Decisão de quem analisa. Muda a condição do instrumento: "
                                "Aprovado → Em uso; Orientação indicativa → segue no "
                                "cronograma; Reprovado - Desativado → sai do cronograma.")
        self.motivo = QLineEdit(placeholderText="Motivo / observação do parecer (opcional)")
        self.avisos = QLabel(wordWrap=True, objectName="avisos")
        self.cancelar = QPushButton("Cancelar")
        self.cancelar.clicked.connect(self.reject)
        self.salvar = QPushButton("SALVAR CORREÇÃO" if self.corrigindo
                                  else "SALVAR CALIBRAÇÃO", objectName="principal")
        self.salvar.clicked.connect(self.salvar_calibracao)

        linha = QHBoxLayout()
        linha.addWidget(self.geral, 2)
        linha.addWidget(QLabel("Parecer final"))
        linha.addWidget(self.parecer, 2)
        linha.addWidget(self.motivo, 3)
        botoes = QHBoxLayout()
        botoes.addWidget(self.avisos, 3)
        botoes.addWidget(self.cancelar, 1)
        botoes.addWidget(self.salvar, 2)
        caixa = QGroupBox("Parecer final")
        coluna = QVBoxLayout(caixa)
        coluna.addLayout(linha)
        coluna.addLayout(botoes)
        return caixa

    def _preencher_com(self, calibracao: Calibracao) -> None:
        """Modo correção: tudo como foi salvo; a data fica travada."""
        data = calibracao.data_calibracao
        self.data.setDate(QDate(data.year, data.month, data.day))
        self.data.setEnabled(False)
        self.data.setToolTip("A data não pode ser corrigida: se estiver errada, envie a "
                             "calibração para a Lixeira e registre de novo.")
        for campo, valor in [(self.laboratorio, calibracao.laboratorio),
                             (self.certificado, calibracao.certificado),
                             (self.responsavel, calibracao.responsavel),
                             (self.custo, numero_em_texto(calibracao.custo)),
                             (self.observacoes, calibracao.observacoes),
                             (self.motivo, calibracao.motivo_parecer)]:
            campo.setText(valor or "")
        self.tabela.blockSignals(True)
        for linha, ponto in enumerate(self.pontos):
            if ponto.resultado == Resultado.NAO_APLICAVEL:
                self.tabela.item(linha, self.NAO_APLICAVEL).setCheckState(Qt.Checked)
            if ponto.tipo in NUMERICOS:
                for coluna, valor in [(self.MEDIDO, ponto.valor),
                                      (self.INCERTEZA, ponto.incerteza),
                                      (self.PADRAO, ponto.valor_padrao),
                                      (self.INDICACAO, ponto.valor_medido)]:
                    item = self.tabela.item(linha, coluna)
                    if item.flags() & Qt.ItemIsEditable:
                        item.setText(numero_em_texto(valor))
            elif ponto.resultado in ESCOLHAS.values():
                self.tabela.cellWidget(linha, self.MEDIDO).setCurrentText(ponto.resultado.value)
            self.tabela.item(linha, self.OBSERVACAO).setText(ponto.observacao or "")
        self.tabela.blockSignals(False)
        for linha in range(len(self.pontos)):
            self._avaliar_linha(linha)
        self.parecer.setCurrentIndex(max(self.parecer.findData(calibracao.parecer_final), 0))

    # --- Avaliação enquanto digita ----------------------------------------------------------

    def _mudou_celula(self, item: QTableWidgetItem) -> None:
        if item.column() != self.RESULTADO:
            self._avaliar_linha(item.row())

    def _texto(self, linha: int, coluna: int) -> str:
        item = self.tabela.item(linha, coluna)
        return item.text() if item and item.flags() & Qt.ItemIsEditable else ""

    def medido_da_linha(self, linha: int) -> PontoMedido:
        """O que foi preenchido na linha. ValueError se um número não for número."""
        ponto = self.pontos[linha]
        medido = PontoMedido(ponto.id, observacao=self._texto(linha, self.OBSERVACAO).strip()
                             or None)
        if self.tabela.item(linha, self.NAO_APLICAVEL).checkState() == Qt.Checked:
            medido.escolha = Resultado.NAO_APLICAVEL
            return medido
        if ponto.tipo in NUMERICOS:
            for coluna, campo, nome in [(self.MEDIDO, "valor", "Medido"),
                                        (self.INCERTEZA, "incerteza", "Incerteza (U)"),
                                        (self.PADRAO, "valor_padrao", "Padrão"),
                                        (self.INDICACAO, "valor_medido", "Indicação")]:
                texto = self._texto(linha, coluna)
                try:
                    setattr(medido, campo, numero(texto))
                except ValueError:
                    raise ValueError(f"Ponto {ponto.ordem}: \"{texto}\" em {nome} não é um "
                                     "número.") from None
        else:
            medido.escolha = ESCOLHAS[self.tabela.cellWidget(linha, self.MEDIDO).currentText()]
        return medido

    def _avaliar_linha(self, linha: int) -> None:
        try:
            avaliacao = self.repo.avaliar_ponto(self.pontos[linha], self.medido_da_linha(linha))
            resultado, motivo = avaliacao.resultado, avaliacao.motivo
        except ValueError:
            resultado, motivo = Resultado.NAO_INFORMADO, "não é um número"
        self.tabela.blockSignals(True)
        item = celula_resultado(resultado, motivo)
        item.setData(Qt.UserRole, resultado)
        self.tabela.setItem(linha, self.RESULTADO, item)
        self.tabela.blockSignals(False)
        self._atualizar_geral()

    def resultados(self) -> list[Resultado]:
        return [self.tabela.item(linha, self.RESULTADO).data(Qt.UserRole)
                for linha in range(self.tabela.rowCount())]

    def _atualizar_geral(self) -> None:
        if not hasattr(self, "parecer"):
            return  # ainda montando a janela
        geral = resultado_geral(self.resultados())
        cor = {Resultado.APROVADO: CORES["certo"], Resultado.REPROVADO: CORES["erro"]}.get(
            geral, CORES["aviso"])
        explicacao = " (falta preencher ou avaliar ponto)" if geral == Resultado.PENDENTE else ""
        self.geral.setText(f'Resultado pelos pontos: <b style="color:{cor}">{geral}</b>'
                           f"{explicacao}")
        escolhido = self.parecer.currentData()
        self.parecer.blockSignals(True)
        self.parecer.clear()
        self.parecer.addItem("— escolha o parecer final —", None)
        for parecer in pareceres_permitidos(geral):
            self.parecer.addItem(parecer.value, parecer)
        self.parecer.setCurrentIndex(max(self.parecer.findData(escolhido), 0))
        self.parecer.blockSignals(False)

    # --- Salvar -----------------------------------------------------------------------------

    def salvar_calibracao(self) -> None:
        erros, medidos = [], []
        for linha in range(self.tabela.rowCount()):
            try:
                medidos.append(self.medido_da_linha(linha))
            except ValueError as erro:
                erros.append(str(erro))
        try:
            custo = numero(self.custo.text().replace("R$", ""))
        except ValueError:
            erros.append("O custo deve ser um número (ex.: 150,00).")
        if erros:
            self._aviso(erros)
            return
        if self.corrigindo:
            self._salvar_correcao(medidos, custo)
            return
        nova = NovaCalibracao(
            self.instrumento.id, self.data.date().toPython(), medidos,
            parecer_final=self.parecer.currentData(),
            motivo_parecer=self.motivo.text().strip() or None,
            laboratorio=self.laboratorio.text().strip() or None,
            certificado=self.certificado.text().strip() or None,
            responsavel=self.responsavel.text().strip() or None,
            custo=custo, observacoes=self.observacoes.text().strip() or None,
        )
        try:
            self.calibracao_id = self.repo.registrar_calibracao(nova, self.hoje)
        except ErroDeValidacao as erro:
            self._aviso(erro.mensagens)
            return
        self.accept()

    def _salvar_correcao(self, medidos: list[PontoMedido], custo: float | None) -> None:
        correcao = CorrecaoCalibracao(
            {medido.ponto_plano_id: medido for medido in medidos},
            parecer_final=self.parecer.currentData(),
            motivo_parecer=self.motivo.text().strip() or None,
            laboratorio=self.laboratorio.text().strip() or None,
            certificado=self.certificado.text().strip() or None,
            responsavel=self.responsavel.text().strip() or None,
            custo=custo, observacoes=self.observacoes.text().strip() or None,
        )
        try:
            self.mudancas = self.repo.corrigir_calibracao(
                self.corrigindo.id, correcao, self.usuario, datetime.datetime.now())
        except ErroDeValidacao as erro:
            self._aviso(erro.mensagens)
            return
        self.accept()

    def _aviso(self, mensagens: list[str]) -> None:
        self.avisos.setStyleSheet(f"color: {CORES['erro']};")
        # Muitos pontos pendentes: mostra os primeiros e quantos faltam.
        mostradas = mensagens[:6]
        if len(mensagens) > 6:
            mostradas.append(f"… e mais {len(mensagens) - 6}.")
        self.avisos.setText("\n".join(f"✖ {m}" for m in mostradas))


class JanelaVerCalibracao(QDialog):
    """Uma calibração já registrada: dados e os pontos como ficaram guardados."""

    def __init__(self, repositorio: Repositorio, instrumento: Instrumento,
                 calibracao: Calibracao, parent=None) -> None:
        super().__init__(parent)
        self.setWindowTitle(f"Calibração de {instrumento.codigo} em "
                            f"{formatar_data(calibracao.data_calibracao)}")
        _maximizar(self)
        dados = [("Data", formatar_data(calibracao.data_calibracao)),
                 ("Próxima", formatar_data(calibracao.data_proxima)),
                 ("Laboratório", calibracao.laboratorio or "—"),
                 ("Certificado", calibracao.certificado or "—"),
                 ("Responsável", calibracao.responsavel or "—"),
                 ("Custo", dinheiro(calibracao.custo)),
                 ("Resultado pelos pontos", calibracao.resultado.value),
                 ("Parecer final", calibracao.parecer_final.value
                  if calibracao.parecer_final else "—"),
                 ("Motivo do parecer", calibracao.motivo_parecer or "—"),
                 ("Observações", calibracao.observacoes or "—")]
        grade = QGridLayout()
        for indice, (rotulo, valor) in enumerate(dados):
            linha, coluna = divmod(indice, 3)
            grade.addWidget(QLabel(f"{rotulo}:"), linha, coluna * 2)
            grade.addWidget(QLabel(f"<b>{valor}</b>", wordWrap=True), linha, coluna * 2 + 1)
            grade.setColumnStretch(coluna * 2 + 1, 1)
        caixa_dados = QGroupBox("Dados da calibração")
        caixa_dados.setLayout(grade)

        pontos = repositorio.pontos_da_calibracao(calibracao.id)
        self.tabela = tabela_somente_leitura(
            ["Nº", "Seção", "Descrição", "Exigido", "Medido (ou erro)", "Incerteza (U)",
             "Padrão", "Indicação", "Resultado", "Observação"])
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabela.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tabela.setRowCount(len(pontos))
        for linha, ponto in enumerate(pontos):
            medido = (numero_em_texto(ponto.valor) if ponto.tipo in NUMERICOS
                      else "—") or "—"
            itens = [celula(str(ponto.ordem)), celula(ponto.secao or ""),
                     celula(ponto.descricao), celula(referencia(ponto)), celula(medido),
                     celula(numero_em_texto(ponto.incerteza) or "—"),
                     celula(numero_em_texto(ponto.valor_padrao) or "—"),
                     celula(numero_em_texto(ponto.valor_medido) or "—"),
                     celula_resultado(ponto.resultado), celula(ponto.observacao or "")]
            for coluna, item in enumerate(itens):
                self.tabela.setItem(linha, coluna, item)
        caixa_pontos = QGroupBox(f"Pontos da calibração — {len(pontos)}")
        QVBoxLayout(caixa_pontos).addWidget(self.tabela)

        correcoes = repositorio.listar_correcoes(calibracao.id)
        self.tabela_correcoes = tabela_somente_leitura(["Quando", "Quem", "O que mudou"])
        self.tabela_correcoes.horizontalHeader().setSectionResizeMode(
            QHeaderView.ResizeToContents)
        self.tabela_correcoes.horizontalHeader().setStretchLastSection(True)
        linhas = [(registro, mudanca) for registro in correcoes for mudanca in registro.mudancas]
        self.tabela_correcoes.setRowCount(len(linhas))
        for linha, (registro, mudanca) in enumerate(linhas):
            for coluna, texto in enumerate([f"{registro.quando:%d/%m/%Y %H:%M}",
                                            registro.usuario, mudanca]):
                self.tabela_correcoes.setItem(linha, coluna, celula(texto))
        caixa_correcoes = QGroupBox(f"Correções feitas — {len(correcoes)}")
        QVBoxLayout(caixa_correcoes).addWidget(self.tabela_correcoes)
        caixa_correcoes.setVisible(bool(correcoes))

        fechar = QPushButton("Fechar")
        fechar.clicked.connect(self.accept)
        rodape = QHBoxLayout()
        rodape.addStretch(3)
        rodape.addWidget(fechar, 1)
        coluna = QVBoxLayout(self)
        coluna.addWidget(QLabel(f"CALIBRAÇÃO — {instrumento.codigo} ({instrumento.tipo})",
                                objectName="titulo", alignment=Qt.AlignCenter))
        coluna.addWidget(caixa_dados)
        coluna.addWidget(caixa_pontos, 3)
        coluna.addWidget(caixa_correcoes, 1)
        coluna.addLayout(rodape)


class PainelCalibracoes(QWidget):
    """Conteúdo da sub-aba Calibrações do instrumento escolhido."""

    alterado = Signal()

    # Laboratório, responsável e observações aparecem em "Ver pontos…".
    COLUNAS = ["Data", "Próxima", "Pelos pontos", "Parecer final", "Certificado", "Custo"]

    def __init__(self, repositorio: Repositorio, hoje: datetime.date) -> None:
        super().__init__()
        self.repo = repositorio
        self.hoje = hoje
        self.instrumento: Instrumento | None = None
        self.calibracoes: list[Calibracao] = []
        self.pode_editar = True
        # Quem corrige fica registrado; a janela principal troca pela identidade da trava.
        self.usuario = f"{getpass.getuser()} - {platform.node()}"

        self.titulo = QLabel(objectName="dica")
        self.tabela = tabela_somente_leitura(self.COLUNAS)
        self.tabela.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabela.horizontalHeader().setStretchLastSection(True)
        self.tabela.doubleClicked.connect(self.ver_calibracao)
        self.avisos = QLabel(wordWrap=True, objectName="avisos")

        self.registrar = QPushButton("Registrar calibração…")
        self.registrar.clicked.connect(self.registrar_calibracao)
        self.ver = QPushButton("Ver pontos…")
        self.ver.clicked.connect(self.ver_calibracao)
        self.corrigir = QPushButton("Corrigir…")
        self.corrigir.setToolTip("Corrigir valores, U, parecer ou dados do certificado da "
                                 "calibração escolhida (a data não muda). A correção fica "
                                 "registrada.")
        self.corrigir.clicked.connect(self.corrigir_calibracao)
        self.grafico = QPushButton("Gráfico de tendência…")
        self.grafico.setToolTip("Erro de cada ponto ao longo das calibrações, com a Incerteza "
                                "(U) e a tolerância.")
        self.grafico.clicked.connect(self.abrir_grafico)
        self.lixeira = QPushButton("Enviar para a Lixeira…")
        self.lixeira.setToolTip("Para calibração registrada por engano. A mudança de condição "
                                "que ela fez é desfeita.")
        self.lixeira.clicked.connect(self.enviar_para_lixeira)
        botoes = QHBoxLayout()
        for botao in (self.registrar, self.ver, self.corrigir, self.grafico, self.lixeira):
            botoes.addWidget(botao, 1)

        coluna = QVBoxLayout(self)
        coluna.addWidget(self.titulo)
        coluna.addWidget(self.tabela, 1)
        coluna.addWidget(self.avisos)
        coluna.addLayout(botoes)
        self.mostrar(None)

    def mostrar(self, instrumento: Instrumento | None) -> None:
        self.instrumento = instrumento
        self.calibracoes = (list(reversed(self.repo.listar_calibracoes(instrumento.id)))
                            if instrumento else [])  # mais recente em cima
        self.tabela.setRowCount(len(self.calibracoes))
        for linha, calibracao in enumerate(self.calibracoes):
            parecer = calibracao.parecer_final
            itens = [celula(formatar_data(calibracao.data_calibracao)),
                     celula(formatar_data(calibracao.data_proxima)),
                     celula_resultado(calibracao.resultado),
                     celula(parecer.value, CORES_PARECER[parecer]) if parecer else celula("—"),
                     celula(calibracao.certificado or "—"), celula(dinheiro(calibracao.custo))]
            itens[0].setData(Qt.UserRole, calibracao.id)
            for coluna, item in enumerate(itens):
                self.tabela.setItem(linha, coluna, item)
        aplicar_destaques(self.tabela)

        bloqueio = self._bloqueio_registrar()
        self.registrar.setEnabled(bloqueio is None)
        self.registrar.setToolTip(bloqueio or "Preencher os pontos do plano e o parecer final.")
        for botao in (self.ver, self.corrigir, self.lixeira):
            botao.setEnabled(bool(self.calibracoes))
        self.grafico.setEnabled(bool(self.calibracoes))
        if instrumento is None:
            self.titulo.setText("Escolha um instrumento na lista.")
        elif self.calibracoes:
            self.titulo.setText(f"{len(self.calibracoes)} calibração(ões) registrada(s) no "
                                "programa. Clique duas vezes numa linha para ver os pontos.")
        else:
            self.titulo.setText("Nenhuma calibração registrada no programa ainda.")
        self._aviso(f"⚠ {bloqueio}" if bloqueio and instrumento and self.pode_editar
                    else "")

    def _bloqueio_registrar(self) -> str | None:
        if self.instrumento is None:
            return "Escolha um instrumento."
        if self.instrumento.plano_id is None:
            return "Instrumento sem plano de calibração: escolha um plano nos dados acima."
        if not self.repo.listar_pontos(self.instrumento.plano_id):
            return "O plano não tem pontos: inclua os pontos na sub-aba Plano de calibração."
        if self.repo.esta_desativado(self.instrumento.id):
            return "Instrumento desativado: mude a condição para voltar a usar antes de calibrar."
        return None

    def selecionada(self) -> Calibracao | None:
        linhas = self.tabela.selectionModel().selectedRows()
        if not linhas:
            return self.calibracoes[0] if self.calibracoes else None  # a mais recente
        return self.calibracoes[linhas[0].row()]

    # --- Ações ------------------------------------------------------------------------------

    def registrar_calibracao(self) -> None:
        janela = JanelaNovaCalibracao(self.repo, self.instrumento, self.hoje, parent=self)
        if janela.exec():
            self.alterado.emit()
            self._aviso("✔ Calibração registrada.", certo=True)

    def ver_calibracao(self) -> None:
        calibracao = self.selecionada()
        if calibracao is not None:
            JanelaVerCalibracao(self.repo, self.instrumento, calibracao, parent=self).exec()

    def corrigir_calibracao(self) -> None:
        calibracao = self.selecionada()
        if calibracao is None:
            return
        janela = JanelaNovaCalibracao(self.repo, self.instrumento, self.hoje, parent=self,
                                      corrigir=calibracao, usuario=self.usuario)
        if janela.exec():
            self.alterado.emit()
            self._aviso(f"✔ Calibração de {formatar_data(calibracao.data_calibracao)} "
                        f"corrigida ({len(janela.mudancas)} mudança(s), registradas em "
                        "\"Ver pontos…\").", certo=True)

    def abrir_grafico(self) -> None:
        from calibracao.interface.grafico_tendencia import JanelaTendencia  # carrega o Matplotlib
        JanelaTendencia(self.repo.tendencia(self.instrumento.id), self.instrumento.codigo,
                        parent=self).exec()

    def enviar_para_lixeira(self) -> None:
        from calibracao.interface.aba_instrumentos import JanelaMotivo
        calibracao = self.selecionada()
        if calibracao is None:
            return
        data = formatar_data(calibracao.data_calibracao)
        janela = JanelaMotivo(
            f"Enviar a calibração de {data} para a Lixeira",
            f"A calibração de {data} sai do histórico e do cronograma. Se o parecer dela mudou "
            "a condição do instrumento, a mudança é desfeita. Dá para restaurar pela Lixeira.",
            parent=self)
        if janela.exec():
            self.descartar(calibracao, janela.motivo.text())

    def descartar(self, calibracao: Calibracao, motivo: str) -> None:
        try:
            self.repo.enviar_para_lixeira(Tipo.CALIBRACAO, calibracao.id, motivo,
                                          datetime.datetime.now())
        except ErroDeValidacao as erro:
            self._aviso("\n".join(f"✖ {m}" for m in erro.mensagens), erro=True)
            return
        self.alterado.emit()
        self._aviso(f"✔ Calibração de {formatar_data(calibracao.data_calibracao)} enviada "
                    "para a Lixeira.", certo=True)

    def definir_edicao(self, pode: bool) -> None:
        """Modo consulta: só ver os pontos e o gráfico; sem registrar, corrigir nem descartar."""
        for botao in (self.registrar, self.corrigir, self.lixeira):
            botao.setVisible(pode)
        self.pode_editar = pode
        self.mostrar(self.instrumento)

    def _aviso(self, texto: str, certo: bool = False, erro: bool = False) -> None:
        cor = CORES["erro"] if erro else CORES["certo"] if certo else CORES["aviso"]
        self.avisos.setStyleSheet(f"color: {cor};")
        self.avisos.setText(texto)
