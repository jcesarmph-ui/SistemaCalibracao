"""Leitor de certificados com IA dentro da Nova calibração (pedido de 2026-11-19).

O leitor é outro projeto (`LeitorCertificadosIA`, ADR 0012 de lá), instalado como biblioteca.
Aqui só fica o encaixe:
- as pastas do leitor (modelo, correções, registro) ficam em `leitor_ia/`, ao lado do banco, na
  pasta de dados da rede — **um aprendizado só para todos**;
- os planos são lidos do próprio banco do programa (o leitor só lê, nunca grava nele);
- quando a pessoa registra no leitor, ele devolve um dicionário (`saida_para_sistema`) e a Nova
  calibração preenche os pontos. Nada é salvo antes de a pessoa conferir e clicar em SALVAR.

O leitor é pesado (OCR + scikit-learn): só é carregado quando alguém clica no botão, para o
programa continuar abrindo rápido.
"""

from __future__ import annotations

import shutil
import sqlite3
from collections.abc import Callable
from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import QWidget

PASTA = "leitor_ia"
# O modelo que vai junto no pacote, copiado para a rede só na primeira vez (fica fora do Git:
# foi treinado com certificados de verdade).
PASTA_INICIAL = "leitor_ia_inicial"

def pasta_inicial() -> Path:
    """Onde está o modelo que vem no pacote: ao lado do programa (no `.exe`) ou, rodando do
    código, em `dados/leitor_ia_inicial` do projeto."""
    import sys

    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent / PASTA_INICIAL
    return Path(__file__).resolve().parents[3] / "dados" / PASTA_INICIAL


_servico = None  # um só por programa aberto: o modelo é carregado uma vez


def caminho_do_banco(conexao: sqlite3.Connection) -> Path:
    """O arquivo do banco aberto (é ao lado dele que fica a pasta do leitor)."""
    for _, nome, arquivo in conexao.execute("PRAGMA database_list"):
        if nome == "main" and arquivo:
            return Path(arquivo)
    raise RuntimeError("O banco não está num arquivo.")


def preparar_pasta(pasta: Path, inicial: Path | None) -> None:
    """Na primeira vez, copia o modelo e as correções que vieram no pacote. Nunca apaga nada
    que já está na pasta (é o aprendizado de todos)."""
    pasta.mkdir(parents=True, exist_ok=True)
    if inicial is None or not inicial.is_dir():
        return
    for origem in inicial.rglob("*"):
        destino = pasta / origem.relative_to(inicial)
        if origem.is_dir():
            destino.mkdir(parents=True, exist_ok=True)
        elif not destino.exists():
            destino.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(origem, destino)


def servico_do_leitor(banco: Path, inicial: Path | None = None):
    """O serviço do leitor apontando para a pasta de dados (carrega a biblioteca só agora)."""
    global _servico
    from leitor_certificados.interface.servico import Pastas, Servico

    pasta = banco.parent / PASTA
    if _servico is None or _servico.pastas.banco != banco:
        preparar_pasta(pasta, inicial)
        _servico = Servico(Pastas(
            marcacao=pasta / "reais_marcacao", ficticios=pasta / "ficticios", banco=banco,
            modelo=pasta / "modelos" / "modelo_atual.joblib",
            rascunhos=pasta / "rascunhos", registro=pasta / "registro" / "registro.db"))
    return _servico


def abrir_leitor(pai: QWidget, pdf: Path, banco: Path, ao_registrar: Callable[[dict], None],
                 inicial: Path | None = None):
    """Abre a janela do leitor já com o PDF. `ao_registrar` recebe a saída quando a pessoa
    registra no leitor; a janela do leitor fecha sozinha."""
    from leitor_certificados.interface.estilo import montar_estilo
    from leitor_certificados.interface.janela import Janela
    from PySide6.QtCore import QTimer

    from calibracao.interface.estilo import tema_claro

    janela = Janela(servico_do_leitor(banco, inicial))
    # Janela de cima, sem "pai": presa à Nova calibração, o Windows dizia "maximizada" mas
    # deixava a janela pequena (medido: 1403 × 638 numa tela de 1920 × 1032). Quem abriu
    # guarda a referência; a modalidade faz a Nova calibração esperar o leitor.
    janela.setWindowModality(Qt.ApplicationModal)
    janela.setAttribute(Qt.WA_DeleteOnClose)

    def registrou(saida: dict) -> None:
        ao_registrar(saida)
        janela.close()

    janela.registrado.connect(registrou)
    # O estilo do leitor na janela dele: o do programa deixava contornos brancos nos painéis.
    # Aplicado antes de medir a tela (o leitor mede ao montar; o estilo muda os tamanhos).
    janela.setStyleSheet(montar_estilo("cinza_claro" if tema_claro() else "preto"))
    janela.ensurePolished()
    janela.centralWidget().layout().activate()
    tela = (pai.screen() if pai is not None else janela.screen()).availableGeometry()
    janela.setGeometry(tela)
    janela.showMaximized()

    def conferir_tamanho() -> None:
        """Se o Windows "perdeu" o maximizar, ocupa a tela à força e maximiza de novo."""
        area = janela.screen().availableGeometry()
        if janela.width() < area.width() - 20 or janela.height() < area.height() - 60:
            janela.showNormal()
            janela.setGeometry(area)
            janela.showMaximized()

    for espera in (0, 300, 1000):
        QTimer.singleShot(espera, janela, conferir_tamanho)
    if janela.servico.modelo is None:
        janela.iniciar()
    # o modelo é preparado em segundo plano; o PDF abre assim que ele ficar pronto
    _abrir_quando_pronto(janela, pdf)
    return janela


def _abrir_quando_pronto(janela, pdf: Path) -> None:
    from PySide6.QtCore import QTimer

    def tentar() -> None:
        if not janela.isVisible():
            return
        if janela.servico.modelo is None or janela.ocupado:
            QTimer.singleShot(300, tentar)
            return
        janela.abrir(pdf)

    QTimer.singleShot(0, tentar)
