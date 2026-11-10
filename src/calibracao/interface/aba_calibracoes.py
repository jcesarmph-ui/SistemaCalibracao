"""Sub-aba Calibrações do instrumento: histórico, registro de calibração e gráfico de tendência.

Registrar abre uma janela maximizada com os pontos do plano: o resultado de cada ponto aparece
enquanto se digita (verde/vermelho/amarelo) e, no fim, quem analisa escolhe o parecer final —
que muda a condição do instrumento (ver `calibracao.regras.condicao`). A mesma janela corrige uma
calibração salva (tudo menos a data); cada correção fica registrada e aparece em "Ver calibração".
"""

import datetime
import getpass
import platform
from pathlib import Path

from PySide6.QtCore import QDate, Qt, Signal
from PySide6.QtWidgets import (
    QAbstractItemView,
    QComboBox,
    QDateEdit,
    QDialog,
    QFileDialog,
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

from calibracao.dados import certificados as arquivos_pdf
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
from calibracao.interface.aba_certificados import abrir_certificado
from calibracao.interface.componentes import (
    RotuloAviso,
    aplicar_destaques,
    celula,
    dinheiro,
    enter_desce,
    formatar_data,
    reais_em_texto,
    tabela_somente_leitura,
)
from calibracao.interface.estilo import CORES, CORES_PARECER, CORES_RESULTADO
from calibracao.interface.painel_plano import numero, numero_em_texto
from calibracao.interface.tema_icones import por_icone
from calibracao.regras.avaliacao import Resultado, desvio_final, resultado_geral
from calibracao.regras.condicao import pareceres_permitidos, so_qualitativos
from calibracao.regras.lixeira import Tipo

DICA_U = ("Incerteza expandida de medição (U), do certificado: quanto o resultado pode variar "
          "para mais ou para menos. Já vem a do plano; troque se o certificado trouxer outra.")
DICA_SEM_NOMINAL = ("Ponto sem nominal fixo (ex.: durômetro, laboratório externo): digite o "
                    "DESVIO que está no certificado, na coluna Desvio encontrado.")
DICA_DESVIO = "Valor encontrado − exigido (calculado sozinho)."
DICA_DESVIO_FINAL = ("Desvio encontrado ± Incerteza (U), do lado que fica mais perto da "
                     "tolerância (ex.: desvio −0,2 e U 0,1 → −0,3). É o que decide o resultado.")
NUMERICOS = ("NUMERICO", "LIMITE")
ESCOLHAS = {"— escolha —": None, "Aprovado": Resultado.APROVADO,
            "Reprovado": Resultado.REPROVADO}


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


def _texto_numero(valor: float | None) -> str:
    if valor is None:
        return "—"
    if abs(valor) < 5e-7:  # nada de "-0" por arredondamento
        valor = 0.0
    return numero_em_texto(valor)


def desvio_encontrado(ponto, valor: float | None) -> float | None:
    """Encontrado − exigido; no ponto sem nominal fixo, o desvio já vem do certificado.
    Ponto de limite não tem desvio (não há um valor exigido para subtrair)."""
    if valor is None or ponto.tipo != "NUMERICO":
        return None
    return valor - ponto.valor_nominal if ponto.valor_nominal is not None else valor


def texto_desvio_final(ponto, valor: float | None, incerteza: float | None) -> str:
    """Desvio ± U do lado mais perto da tolerância; no limite, o encontrado ± U mais perto do
    limite (pedido de 2026-11-04)."""
    if ponto.tipo == "NUMERICO":
        x = desvio_encontrado(ponto, valor)
        minimo, maximo = ponto.tolerancia_inferior, ponto.tolerancia_superior
    elif ponto.tipo == "LIMITE":
        x, minimo, maximo = valor, ponto.valor_minimo, ponto.valor_maximo
    else:
        return "—"
    final = desvio_final(x, incerteza, minimo, maximo, bool(ponto.incerteza_nao_aplica))
    if final is None:
        return "—"
    if final.dos_dois_lados:
        return f"± {_texto_numero(final.valor)}"
    return _texto_numero(final.valor)


def celula_resultado(resultado: Resultado, motivo: str | None = None) -> QTableWidgetItem:
    texto = f"{resultado.value} — {motivo}" if motivo else resultado.value
    return celula(texto, CORES_RESULTADO[resultado])


def _maximizar(janela: QDialog) -> None:
    janela.setWindowFlags(janela.windowFlags() | Qt.WindowMaximizeButtonHint)
    janela.setWindowState(Qt.WindowMaximized)


NAO_SE_APLICA = "não se aplica"
DICA_NAO_SE_APLICA = ("Incerteza não se aplica a este ponto: ele é avaliado só pelo valor "
                      "medido (dá para mudar na edição do plano).")


class JanelaNovaCalibracao(QDialog):
    """Registrar calibração: dados do certificado, pontos medidos e parecer final.

    Com `corrigir`, a janela vem preenchida com a calibração salva para corrigir; os pontos são os
    da "foto" guardada com ela (não os do plano atual) e a data não muda.
    """

    # Colunas da tabela de pontos
    (NUM, SECAO, DESCRICAO, REFERENCIA, ENCONTRADO, INCERTEZA, DESVIO, DESVIO_FINAL, PADRAO,
     INDICACAO, NAO_APLICAVEL, OBSERVACAO, RESULTADO) = range(13)

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
        self.pdf_escolhido: Path | None = None   # PDF novo escolhido nesta janela
        self.erro_pdf: str | None = None          # salvou a calibração, mas o PDF não foi
        self.pdf_atual = (repositorio.certificado_da_calibracao(corrigir.id) if corrigir
                          else None)
        self.pontos: list[PontoPlano] | list[PontoRegistrado] = (
            repositorio.pontos_da_calibracao(corrigir.id) if corrigir
            else repositorio.pontos_para_calibrar(instrumento))
        acao = "Editar" if corrigir else "Nova"  # o mesmo nome dos botões EDITAR e NOVA CALIBRAÇÃO
        self.setWindowTitle(f"{acao} calibração — {instrumento.codigo}")
        _maximizar(self)

        texto = f"{acao.upper()} CALIBRAÇÃO — {instrumento.codigo}"
        if corrigir:
            texto += f" DE {formatar_data(corrigir.data_calibracao)}"
        titulo = QLabel(texto, objectName="titulo", alignment=Qt.AlignCenter)
        coluna = QVBoxLayout(self)
        coluna.addWidget(titulo)
        if not corrigir and so_qualitativos(instrumento.tipo, instrumento.localizacao):
            coluna.addWidget(QLabel(
                "Trena com orientação indicativa: só os pontos qualitativos entram na "
                "calibração (os numéricos não são medidos).", objectName="dica",
                alignment=Qt.AlignCenter))
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
        # Feita depois do mês previsto: campo opcional para o motivo (sem alarde).
        self.prevista = self._prevista_antes()
        self.aviso_atraso = RotuloAviso(objectName="avisos")
        self.motivo_atraso = QLineEdit(placeholderText="Motivo do atraso (opcional)")
        if self.corrigindo is None:
            pendente = self.repo.motivos_atraso_pendentes().get(self.instrumento.id)
            self.motivo_atraso.setText(pendente or "")
        grade.addWidget(self.aviso_atraso, 2, 0, 1, 2)
        grade.addWidget(self.motivo_atraso, 2, 2, 1, 4)
        # PDF do certificado (pedido de 2026-11-10): opcional; um por calibração, trocável.
        self.nome_pdf = QLabel(wordWrap=True)
        self.escolher_pdf = QPushButton("Substituir certificado (PDF)" if self.pdf_atual
                                        else "Adicionar certificado (PDF)")
        por_icone(self.escolher_pdf, "attach_file", CORES["titulo"])
        self.escolher_pdf.setToolTip(
            "PDF do certificado (opcional). Ele é copiado para a pasta dos certificados do "
            "programa; o seu arquivo continua onde está. Trocar manda o anterior para a Lixeira.")
        self.escolher_pdf.clicked.connect(self.procurar_pdf)
        grade.addWidget(QLabel("Certificado (PDF)"), 3, 0)
        grade.addWidget(self.nome_pdf, 3, 1, 1, 3)
        grade.addWidget(self.escolher_pdf, 3, 4, 1, 2)
        # A caixa primeiro: mostrar um campo ainda sem "pai" pisca uma janela solta na tela.
        caixa = QGroupBox("Dados da calibração")
        caixa.setLayout(grade)
        self._mostrar_pdf()
        self.data.dateChanged.connect(lambda _: self._mostrar_atraso())
        self._mostrar_atraso()
        return caixa

    def _prevista_antes(self) -> datetime.date | None:
        """A data que estava prevista para esta calibração (a partir da anterior)."""
        if self.corrigindo is None:
            return self.repo.prevista_atual(self.instrumento.id)
        calibracoes = self.repo.listar_calibracoes(self.instrumento.id)
        ids = [c.id for c in calibracoes]
        posicao = ids.index(self.corrigindo.id) if self.corrigindo.id in ids else 0
        return calibracoes[posicao - 1].data_proxima if posicao > 0 else None

    def atrasada(self) -> bool:
        data = self.data.date().toPython()
        return self.prevista is not None and (data.year, data.month) > (
            self.prevista.year, self.prevista.month)

    def _mostrar_atraso(self) -> None:
        mostrar = self.atrasada() or bool(self.motivo_atraso.text())
        self.aviso_atraso.setText(
            f"⚠ Prevista para {formatar_data(self.prevista)}: feita depois do mês previsto."
            if self.atrasada() else "Motivo do atraso:")
        self.aviso_atraso.setVisible(mostrar)
        self.motivo_atraso.setVisible(mostrar)

    def _caixa_pontos(self) -> QGroupBox:
        colunas = [
            ("Nº", ""), ("Seção", ""), ("Descrição", ""), ("Exigido", "O que o ponto exige."),
            ("Valor encontrado", "Valor medido na calibração. Em ponto de verificação, "
                                 "escolha o resultado."),
            ("Incerteza (U)", DICA_U),
            ("Desvio encontrado", DICA_DESVIO + " Em ponto sem nominal fixo, digite o desvio "
                                                "do certificado."),
            ("Desvio final", DICA_DESVIO_FINAL),
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
        # Um clique (ou começar a digitar) já edita; Enter confirma e desce (pedido de 2026-11-04).
        self.tabela.setEditTriggers(QAbstractItemView.AllEditTriggers)
        enter_desce(self.tabela)

        self.tabela.blockSignals(True)
        for linha, ponto in enumerate(self.pontos):
            self._montar_linha(linha, ponto)
        self.tabela.blockSignals(False)
        self.tabela.itemChanged.connect(self._mudou_celula)
        for linha in range(len(self.pontos)):
            self._avaliar_linha(linha)

        sem_nominal = sum(1 for p in self.pontos if p.tipo == "NUMERICO"
                          and p.valor_nominal is None)
        dica = ("Preencha todos os pontos: ponto em branco não deixa salvar. Clique numa célula "
                "(ou comece a digitar) para preencher; Enter confirma e desce para a de baixo.")
        if sem_nominal:
            dica += (f" {sem_nominal} ponto(s) sem nominal fixo: digite o desvio do certificado "
                     "em Desvio encontrado.")
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
            if ponto.tipo == "NUMERICO" and ponto.valor_nominal is None:
                # sem nominal fixo: o certificado já traz o desvio
                self._fixo(linha, self.ENCONTRADO, "—")
                self._editavel(linha, self.DESVIO)
                self.tabela.item(linha, self.DESVIO).setToolTip(DICA_SEM_NOMINAL)
            else:
                self._editavel(linha, self.ENCONTRADO)
                self._fixo(linha, self.DESVIO, "—")
            self._fixo(linha, self.DESVIO_FINAL, "—")
            if ponto.incerteza_nao_aplica:  # "-" ou "N/A" na DQ05: avaliado só pelo valor
                self._fixo(linha, self.INCERTEZA, NAO_SE_APLICA)
                self.tabela.item(linha, self.INCERTEZA).setToolTip(DICA_NAO_SE_APLICA)
            else:
                self._editavel(linha, self.INCERTEZA, numero_em_texto(ponto.incerteza))
            if ponto.tipo == "NUMERICO" and ponto.valor_nominal is None:
                self._editavel(linha, self.PADRAO)
                self._editavel(linha, self.INDICACAO)
            else:
                self._fixo(linha, self.PADRAO, "—")
                self._fixo(linha, self.INDICACAO, "—")
        else:
            escolha = QComboBox()
            escolha.addItems(ESCOLHAS)
            escolha.currentIndexChanged.connect(lambda _, n=linha: self._avaliar_linha(n))
            self.tabela.setCellWidget(linha, self.ENCONTRADO, escolha)
            for coluna in (self.INCERTEZA, self.DESVIO, self.DESVIO_FINAL, self.PADRAO,
                           self.INDICACAO):
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
        self.parecer.setToolTip("Decisão de quem analisa. Aprovado → Em uso; Orientação "
                                "indicativa → Em uso e com a marca de orientação indicativa; "
                                "Reprovado - Desativado → sai do cronograma.")
        self.motivo = QLineEdit(placeholderText="Motivo / observação do parecer (opcional)")
        self.avisos = RotuloAviso(wordWrap=True, objectName="avisos")
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
                             (self.custo, reais_em_texto(calibracao.custo)),  # sempre com centavos
                             (self.observacoes, calibracao.observacoes),
                             (self.motivo, calibracao.motivo_parecer),
                             (self.motivo_atraso, calibracao.motivo_atraso)]:
            campo.setText(valor or "")
        self._mostrar_atraso()
        self.tabela.blockSignals(True)
        for linha, ponto in enumerate(self.pontos):
            if ponto.resultado == Resultado.NAO_APLICAVEL:
                self.tabela.item(linha, self.NAO_APLICAVEL).setCheckState(Qt.Checked)
            if ponto.tipo in NUMERICOS:
                for coluna, valor in [(self.ENCONTRADO, ponto.valor),
                                      (self.DESVIO, ponto.valor),
                                      (self.INCERTEZA, ponto.incerteza),
                                      (self.PADRAO, ponto.valor_padrao),
                                      (self.INDICACAO, ponto.valor_medido)]:
                    item = self.tabela.item(linha, coluna)
                    if item.flags() & Qt.ItemIsEditable:
                        item.setText(numero_em_texto(valor))
            elif ponto.resultado in ESCOLHAS.values():
                self.tabela.cellWidget(linha, self.ENCONTRADO).setCurrentText(
                    ponto.resultado.value)
            self.tabela.item(linha, self.OBSERVACAO).setText(ponto.observacao or "")
        self.tabela.blockSignals(False)
        for linha in range(len(self.pontos)):
            self._avaliar_linha(linha)
        self.parecer.setCurrentIndex(max(self.parecer.findData(calibracao.parecer_final), 0))

    # --- Avaliação enquanto digita ----------------------------------------------------------

    def _mudou_celula(self, item: QTableWidgetItem) -> None:
        if item.column() != self.RESULTADO:
            self._avaliar_linha(item.row())

    def _editavel_em(self, linha: int, coluna: int) -> bool:
        item = self.tabela.item(linha, coluna)
        return bool(item and item.flags() & Qt.ItemIsEditable)

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
            # o valor é o encontrado ou, sem nominal fixo, o desvio (só uma das duas é editável)
            valor = self._texto(linha, self.ENCONTRADO) or self._texto(linha, self.DESVIO)
            nome_valor = ("Desvio encontrado" if self._editavel_em(linha, self.DESVIO)
                          else "Valor encontrado")
            for texto, campo, nome in [
                    (valor, "valor", nome_valor),
                    (self._texto(linha, self.INCERTEZA), "incerteza", "Incerteza (U)"),
                    (self._texto(linha, self.PADRAO), "valor_padrao", "Padrão"),
                    (self._texto(linha, self.INDICACAO), "valor_medido", "Indicação")]:
                try:
                    setattr(medido, campo, numero(texto))
                except ValueError:
                    raise ValueError(f"Ponto {ponto.ordem}: \"{texto}\" em {nome} não é um "
                                     "número.") from None
        else:
            medido.escolha = ESCOLHAS[
                self.tabela.cellWidget(linha, self.ENCONTRADO).currentText()]
        return medido

    def _avaliar_linha(self, linha: int) -> None:
        ponto = self.pontos[linha]
        medido = None
        try:
            medido = self.medido_da_linha(linha)
            avaliacao = self.repo.avaliar_ponto(ponto, medido)
            resultado, motivo = avaliacao.resultado, avaliacao.motivo
        except ValueError:
            resultado, motivo = Resultado.NAO_INFORMADO, "não é um número"
        self.tabela.blockSignals(True)
        if ponto.tipo in NUMERICOS:
            conta = medido is not None and medido.escolha != Resultado.NAO_APLICAVEL
            valor = medido.valor if conta else None
            if not self._editavel_em(linha, self.DESVIO):
                self.tabela.item(linha, self.DESVIO).setText(
                    _texto_numero(desvio_encontrado(ponto, valor)))
            self.tabela.item(linha, self.DESVIO_FINAL).setText(
                texto_desvio_final(ponto, valor, medido.incerteza if conta else None))
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
            motivo_atraso=self._motivo_atraso(),
        )
        if not self._pdf_ainda_serve():
            return
        try:
            self.calibracao_id = self.repo.registrar_calibracao(nova, self.hoje)
        except ErroDeValidacao as erro:
            self._aviso(erro.mensagens)
            return
        self._guardar_pdf()
        self.accept()

    def _motivo_atraso(self) -> str | None:
        """Só vale se a calibração ficou atrasada (ou se já tinha um motivo guardado)."""
        if not self.motivo_atraso.isVisible() and not self.atrasada():
            return None
        return self.motivo_atraso.text().strip() or None

    def _salvar_correcao(self, medidos: list[PontoMedido], custo: float | None) -> None:
        correcao = CorrecaoCalibracao(
            {medido.ponto_plano_id: medido for medido in medidos},
            parecer_final=self.parecer.currentData(),
            motivo_parecer=self.motivo.text().strip() or None,
            laboratorio=self.laboratorio.text().strip() or None,
            certificado=self.certificado.text().strip() or None,
            responsavel=self.responsavel.text().strip() or None,
            custo=custo, observacoes=self.observacoes.text().strip() or None,
            motivo_atraso=self._motivo_atraso(),
        )
        if not self._pdf_ainda_serve():
            return
        try:
            self.mudancas = self.repo.corrigir_calibracao(
                self.corrigindo.id, correcao, self.usuario, datetime.datetime.now())
        except ErroDeValidacao as erro:
            # Só trocou o PDF: não é erro (a troca fica registrada no próprio PDF guardado).
            if not (self.pdf_escolhido and erro.mensagens == ["Nada foi alterado."]):
                self._aviso(erro.mensagens)
                return
        self._guardar_pdf()
        self.accept()

    # --- PDF do certificado -------------------------------------------------------------------

    def _mostrar_pdf(self) -> None:
        if self.pdf_escolhido:
            texto = f"<b>{self.pdf_escolhido.name}</b> — será guardado ao salvar"
            if self.pdf_atual:
                texto += f" (o atual, {self.pdf_atual.nome_original}, vai para a Lixeira)"
        elif self.pdf_atual:
            enviado = datetime.datetime.fromisoformat(self.pdf_atual.enviado_em)
            texto = (f"<b>{self.pdf_atual.nome_original}</b> — guardado em "
                     f"{enviado:%d/%m/%Y %H:%M}")
        else:
            texto = f'<span style="color:{CORES["dica"]}"><i>Nenhum PDF (opcional)</i></span>'
        self.nome_pdf.setText(texto)

    def procurar_pdf(self) -> None:
        arquivo, _ = QFileDialog.getOpenFileName(
            self, "Escolher o PDF do certificado", str(Path.home()), "PDF (*.pdf)")
        if arquivo:
            self.usar_pdf(Path(arquivo))

    def usar_pdf(self, arquivo: Path) -> bool:
        """Confere o arquivo na hora (PDF de verdade, tamanho) e guarda a escolha."""
        try:
            arquivos_pdf.conferir_pdf(arquivo)
        except arquivos_pdf.ErroDoArquivo as erro:
            self._aviso([str(erro)])
            return False
        self.pdf_escolhido = arquivo
        self.avisos.setText("")
        self._mostrar_pdf()
        return True

    def _pdf_ainda_serve(self) -> bool:
        """Confere de novo antes de salvar (o arquivo pode ter sumido ou mudado)."""
        if self.pdf_escolhido is None:
            return True
        try:
            arquivos_pdf.conferir_pdf(self.pdf_escolhido)
        except arquivos_pdf.ErroDoArquivo as erro:
            self._aviso([f"PDF do certificado: {erro}"])
            return False
        return True

    def _guardar_pdf(self) -> None:
        """Depois que a calibração foi salva. Se o PDF falhar (ex.: rede caiu), a calibração
        fica salva e quem abriu a janela mostra o aviso para anexar pelo EDITAR."""
        if self.pdf_escolhido is None:
            return
        try:
            self.repo.anexar_certificado(self.calibracao_id, self.pdf_escolhido,
                                         self.usuario or None, datetime.datetime.now())
        except (ErroDeValidacao, OSError) as erro:
            motivo = " ".join(erro.mensagens) if isinstance(erro, ErroDeValidacao) else str(erro)
            self.erro_pdf = (f"A calibração foi salva, mas o PDF não foi guardado: {motivo} "
                             "Anexe de novo pelo EDITAR da calibração.")

    def _aviso(self, mensagens: list[str]) -> None:
        self.avisos.setStyleSheet(f"color: {CORES['erro']};")
        # Muitos pontos pendentes: mostra os primeiros e quantos faltam.
        mostradas = mensagens[:6]
        if len(mensagens) > 6:
            mostradas.append(f"… e mais {len(mensagens) - 6}.")
        self.avisos.setText("\n".join(f"✖ {m}" for m in mostradas))


class JanelaVerCalibracao(QDialog):
    """Uma calibração já registrada: dados e os pontos como ficaram guardados — só apresentação.

    Para mexer, o botão EDITAR (só no modo edição) fecha esta janela com `EDITAR` e quem abriu
    abre a janela de correção (pedido do usuário em 2026-11-03).
    """

    EDITAR = 2

    def __init__(self, repositorio: Repositorio, instrumento: Instrumento,
                 calibracao: Calibracao, parent=None, pode_editar: bool = False) -> None:
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
        self.repo = repositorio
        self.pdf = repositorio.certificado_da_calibracao(calibracao.id)
        dados.append(("Certificado (PDF)", self.pdf.nome_original if self.pdf
                      else "nenhum PDF guardado"))
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
            ["Nº", "Seção", "Descrição", "Exigido", "Valor encontrado", "Incerteza (U)",
             "Desvio encontrado", "Desvio final", "Padrão", "Indicação", "Resultado",
             "Observação"])
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabela.horizontalHeader().setSectionResizeMode(3, QHeaderView.Stretch)
        self.tabela.setRowCount(len(pontos))
        for linha, ponto in enumerate(pontos):
            sem_nominal = ponto.tipo == "NUMERICO" and ponto.valor_nominal is None
            numerico = ponto.tipo in NUMERICOS
            encontrado = (_texto_numero(ponto.valor) if numerico and not sem_nominal
                          else "—")
            itens = [celula(str(ponto.ordem)), celula(ponto.secao or ""),
                     celula(ponto.descricao), celula(referencia(ponto)), celula(encontrado),
                     celula(NAO_SE_APLICA if ponto.incerteza_nao_aplica
                            else numero_em_texto(ponto.incerteza) or "—"),
                     celula(_texto_numero(desvio_encontrado(ponto, ponto.valor))),
                     celula(texto_desvio_final(ponto, ponto.valor, ponto.incerteza)),
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
        if not correcoes:  # só esconder aqui: mostrar algo ainda sem "pai" pisca uma janela
            caixa_correcoes.hide()

        self.editar = QPushButton("EDITAR")
        por_icone(self.editar, "edit", CORES["titulo"])
        self.editar.setToolTip("Corrigir valores, U, parecer ou dados do certificado desta "
                               "calibração (a data não muda). A correção fica registrada.")
        self.editar.clicked.connect(lambda: self.done(self.EDITAR))
        if not pode_editar:
            self.editar.hide()
        self.abrir_pdf = QPushButton("Abrir PDF")
        por_icone(self.abrir_pdf, "picture_as_pdf", CORES["titulo"])
        self.abrir_pdf.setToolTip("Abre o PDF do certificado no programa de PDF do Windows.")
        self.abrir_pdf.clicked.connect(self.abrir_o_pdf)
        if self.pdf is None:
            self.abrir_pdf.hide()
        self.aviso_pdf = RotuloAviso(wordWrap=True, objectName="avisos")
        fechar = QPushButton("Fechar")
        fechar.clicked.connect(self.accept)
        rodape = QHBoxLayout()
        rodape.addWidget(self.aviso_pdf, 2)
        rodape.addWidget(self.abrir_pdf, 1)
        rodape.addWidget(self.editar, 1)
        rodape.addWidget(fechar, 1)
        coluna = QVBoxLayout(self)
        coluna.addWidget(QLabel(f"CALIBRAÇÃO — {instrumento.codigo}",
                                objectName="titulo", alignment=Qt.AlignCenter))
        coluna.addWidget(QLabel("Só para ver. Para mudar algo, clique em EDITAR.",
                                objectName="dica", alignment=Qt.AlignCenter))
        coluna.addWidget(caixa_dados)
        coluna.addWidget(caixa_pontos, 3)
        coluna.addWidget(caixa_correcoes, 1)
        coluna.addLayout(rodape)

    def abrir_o_pdf(self) -> None:
        texto, tipo = abrir_certificado(self.repo, self.pdf)
        cor = {"certo": CORES["certo"], "erro": CORES["erro"]}.get(tipo, CORES["aviso"])
        self.aviso_pdf.setStyleSheet(f"color: {cor};")
        self.aviso_pdf.setText(texto)


class PainelCalibracoes(QWidget):
    """Calibrações do instrumento escolhido (aba Calibrar): NOVA CALIBRAÇÃO em cima, a lista das
    feitas e, ao clicar numa delas, a janela só de apresentação (com EDITAR)."""

    alterado = Signal()

    # Laboratório, responsável e observações aparecem em "Ver calibração".
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
        self.tabela.setProperty("clicavel", True)  # clicar na linha abre a calibração
        self.tabela.viewport().setCursor(Qt.PointingHandCursor)
        self.tabela.setSelectionMode(QAbstractItemView.SingleSelection)
        self.tabela.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeToContents)
        self.tabela.horizontalHeader().setStretchLastSection(True)
        self.tabela.clicked.connect(self.ver_calibracao)
        self.avisos = RotuloAviso(wordWrap=True, objectName="avisos")

        self.registrar = QPushButton("NOVA CALIBRAÇÃO", objectName="principal")
        self.registrar.clicked.connect(self.registrar_calibracao)
        self.ver = QPushButton("Ver calibração")
        por_icone(self.ver, "visibility", CORES["titulo"])
        self.ver.setToolTip("Abre a calibração escolhida (a mais recente, se nenhuma estiver "
                            "escolhida). Também abre clicando na linha.")
        self.ver.clicked.connect(self.ver_calibracao)
        self.grafico = QPushButton("Gráfico de tendência")
        por_icone(self.grafico, "show_chart", CORES["titulo"])
        self.grafico.setToolTip("Erro de cada ponto ao longo das calibrações, com a Incerteza "
                                "(U) e a tolerância.")
        self.grafico.clicked.connect(self.abrir_grafico)
        self.lixeira = QPushButton("Enviar para a Lixeira")
        por_icone(self.lixeira, "delete", CORES["titulo"])
        self.lixeira.setToolTip("Para calibração registrada por engano. A mudança de condição "
                                "que ela fez é desfeita.")
        self.lixeira.clicked.connect(self.enviar_para_lixeira)
        botoes = QHBoxLayout()
        for botao in (self.ver, self.grafico, self.lixeira):
            botoes.addWidget(botao, 1)

        coluna = QVBoxLayout(self)
        coluna.setContentsMargins(0, 0, 0, 0)
        coluna.addWidget(self.registrar)
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
        for botao in (self.ver, self.lixeira):
            botao.setEnabled(bool(self.calibracoes))
        self.grafico.setEnabled(bool(self.calibracoes))
        if instrumento is None:
            self.titulo.setText("Escolha um instrumento na lista.")
        elif self.calibracoes:
            self.titulo.setText(f"{len(self.calibracoes)} calibração(ões) registrada(s) no "
                                "programa. Clique numa linha para ver a calibração.")
        else:
            self.titulo.setText("Nenhuma calibração registrada no programa ainda.")
        self._aviso(f"⚠ {bloqueio}" if bloqueio and instrumento and self.pode_editar
                    else "")

    def _bloqueio_registrar(self) -> str | None:
        if self.instrumento is None:
            return "Escolha um instrumento."
        if self.instrumento.plano_id is None:
            return ("Instrumento sem plano de calibração: escolha um plano na aba "
                    "Instrumentos.")
        if not self.repo.listar_pontos(self.instrumento.plano_id):
            return "O plano não tem pontos: inclua os pontos na aba Instrumentos."
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
        janela = JanelaNovaCalibracao(self.repo, self.instrumento, self.hoje, parent=self,
                                      usuario=self.usuario)
        if janela.exec():
            self.alterado.emit()
            if janela.erro_pdf:
                self._aviso(f"✖ {janela.erro_pdf}", erro=True)
            else:
                self._aviso("✔ Calibração registrada.", certo=True)

    def ver_calibracao(self) -> None:
        calibracao = self.selecionada()
        if calibracao is None:
            return
        janela = JanelaVerCalibracao(self.repo, self.instrumento, calibracao, parent=self,
                                     pode_editar=self.pode_editar)
        if janela.exec() == JanelaVerCalibracao.EDITAR:
            self.corrigir_calibracao(calibracao)

    def corrigir_calibracao(self, calibracao: Calibracao | None = None) -> None:
        calibracao = calibracao or self.selecionada()
        if calibracao is None:
            return
        janela = JanelaNovaCalibracao(self.repo, self.instrumento, self.hoje, parent=self,
                                      corrigir=calibracao, usuario=self.usuario)
        if janela.exec():
            self.alterado.emit()
            data = formatar_data(calibracao.data_calibracao)
            if janela.erro_pdf:
                self._aviso(f"✖ {janela.erro_pdf}", erro=True)
            elif not janela.mudancas:
                self._aviso(f"✔ PDF do certificado da calibração de {data} guardado.",
                            certo=True)
            else:
                pdf = " e o PDF guardado" if janela.pdf_escolhido else ""
                self._aviso(f"✔ Calibração de {data} corrigida ({len(janela.mudancas)} "
                            f"mudança(s), registradas em \"Ver calibração\"){pdf}.", certo=True)

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
        """Modo consulta: só ver as calibrações e o gráfico; sem registrar, editar nem
        descartar (o EDITAR some da janela de ver)."""
        for botao in (self.registrar, self.lixeira):
            botao.setVisible(pode)
        self.pode_editar = pode
        self.mostrar(self.instrumento)

    def _aviso(self, texto: str, certo: bool = False, erro: bool = False) -> None:
        cor = CORES["erro"] if erro else CORES["certo"] if certo else CORES["aviso"]
        self.avisos.setStyleSheet(f"color: {cor};")
        self.avisos.setText(texto)
