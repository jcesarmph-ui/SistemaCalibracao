"""Modo claro e escuro (pedido de 2026-11-10): cores com nome, botão sol/lua, troca na hora e
escolha guardada para cada pessoa."""

import os
from datetime import date

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QSettings, Qt  # noqa: E402
from PySide6.QtGui import QColor, QPixmap  # noqa: E402
from PySide6.QtWidgets import QApplication, QPushButton  # noqa: E402

from calibracao.dados.repositorio import Repositorio  # noqa: E402
from calibracao.interface import estilo, preferencias  # noqa: E402
from calibracao.interface import janela as modulo_janela  # noqa: E402
from calibracao.interface.janela import JanelaPrincipal, logo_com_letra_preta  # noqa: E402
from calibracao.interface.tema_icones import por_icone, repintar_icones  # noqa: E402
from calibracao.regras.avaliacao import Resultado  # noqa: E402

HOJE = date(2026, 11, 10)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse=True)
def volta_ao_escuro():
    yield
    estilo.aplicar_tema("escuro")  # o tema é do programa inteiro: não vazar para outro teste


@pytest.fixture
def gravados(monkeypatch):
    lista = []
    monkeypatch.setattr(modulo_janela, "gravar_tema", lista.append)
    return lista


@pytest.fixture
def janela(app, tmp_path, gravados):
    repo = Repositorio.abrir(tmp_path / "calibracao.db", HOJE)
    tela = JanelaPrincipal(repo, tmp_path, HOJE)
    yield tela
    tela.close()
    repo.fechar()


def test_os_dois_temas_tem_as_mesmas_cores():
    assert set(estilo.TEMAS) == {"escuro", "claro"}
    assert set(estilo.ESCURO) == set(estilo.CLARO)


def test_aplicar_tema_troca_as_cores_e_a_faixa_neutra():
    estilo.aplicar_tema("claro")
    assert estilo.tema_claro() and estilo.CORES["fundo"] == estilo.CLARO["fundo"]
    assert estilo.CORES_RESULTADO[Resultado.NAO_APLICAVEL] == (
        estilo.CLARO["neutra_fundo"], estilo.CLARO["neutra_letra"])
    assert estilo.CLARO["fundo"] in estilo.estilo()  # todo nome de cor do estilo existe no tema
    estilo.aplicar_tema("qualquer coisa")
    assert estilo.tema_atual() == "escuro"
    assert estilo.CORES_RESULTADO[Resultado.NAO_APLICAVEL] == (
        estilo.ESCURO["neutra_fundo"], estilo.ESCURO["neutra_letra"])


def test_botao_sol_lua_troca_na_hora_e_guarda_a_escolha(janela, gravados):
    botao = janela.botao_tema
    assert botao.toolTip() == "Mudar para modo claro"
    assert botao.cursor().shape() == Qt.PointingHandCursor
    botao.click()
    assert estilo.tema_claro() and gravados == ["claro"]
    assert botao.toolTip() == "Mudar para modo escuro"
    assert estilo.CLARO["fundo"] in janela.styleSheet()
    botao.click()
    assert estilo.tema_atual() == "escuro" and gravados == ["claro", "escuro"]
    assert botao.toolTip() == "Mudar para modo claro"


def test_icones_sao_repintados_na_cor_do_tema_novo(app):
    botao = QPushButton("Editar")
    por_icone(botao, "edit", estilo.ESCURO["titulo"])
    assert repintar_icones(estilo.ESCURO, estilo.CLARO) >= 1
    cor = botao.icon().pixmap(22, 22).toImage().pixelColor(11, 11)  # meio do lápis
    assert cor.alpha() == 0 or cor.lightness() < 128  # escuro sobre fundo claro


def test_logo_com_letra_preta_nao_mexe_no_simbolo(app):
    imagem = QPixmap(100, 10)
    imagem.fill(QColor("#ffffff"))
    resultado = logo_com_letra_preta(imagem).toImage()
    assert resultado.pixelColor(10, 5).name() == "#ffffff"   # símbolo (até 30%) continua
    assert resultado.pixelColor(31, 5).name() == "#000000"   # o traço vertical fica preto
    assert resultado.pixelColor(90, 5).name() == "#000000"   # as letras ficam pretas


def test_preferencia_fica_guardada_para_a_pessoa(tmp_path, monkeypatch):
    arquivo = str(tmp_path / "preferencias.ini")
    monkeypatch.setattr(preferencias, "_configuracoes",
                        lambda: QSettings(arquivo, QSettings.IniFormat))
    assert preferencias.ler_tema() == "escuro"  # padrão
    preferencias.gravar_tema("claro")
    assert preferencias.ler_tema() == "claro"
    preferencias.gravar_tema("roxo")
    assert preferencias.ler_tema() == "escuro"  # valor estranho = padrão


def test_icone_do_botao_vermelho_fica_branco_nos_dois_temas(app):
    botao = QPushButton("EDITAR", objectName="principal")
    estilo.aplicar_tema("claro")
    por_icone(botao, "edit", estilo.CORES["titulo"])
    repintar_icones(estilo.CLARO, estilo.ESCURO)
    imagem = botao.icon().pixmap(22, 22).toImage()
    visiveis = [imagem.pixelColor(x, y) for x in range(22) for y in range(22)
                if imagem.pixelColor(x, y).alpha() > 200]
    assert visiveis and all(cor.lightness() > 200 for cor in visiveis)
