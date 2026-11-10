"""Melhorias do cadastro de instrumento da versão 1.2.0 (pedidos do usuário em 2026-11-10)."""

import os
from datetime import date

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QDate  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from calibracao.dados.repositorio import Instrumento, Repositorio  # noqa: E402
from calibracao.interface.componentes import (  # noqa: E402
    data_livre_para_banco,
    data_livre_para_tela,
)
from calibracao.interface.janela import JanelaPrincipal  # noqa: E402

HOJE = date(2026, 11, 10)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def janela(app, tmp_path):
    repo = Repositorio.abrir(tmp_path / "calibracao.db", HOJE)
    for codigo, tipo, local in [("PAQ-017", "Paquímetro", "CT-01"),
                                ("PAQ-018", "Paquímetro", "Serralheria / Manutenção"),
                                ("TRE-009", "Trena", "Manutenção")]:
        repo.incluir_instrumento(Instrumento(codigo, tipo, localizacao=local,
                                             data_compra="2023-11-16"))
    tela = JanelaPrincipal(repo, tmp_path, HOJE)
    yield tela
    tela.close()
    repo.fechar()


def test_data_de_compra_aparece_dd_mm_aaaa_e_texto_livre_fica_igual():
    assert data_livre_para_tela("2023-11-16") == "16/11/2023"
    assert data_livre_para_tela("Transferida para Filial 1") == "Transferida para Filial 1"
    assert data_livre_para_tela(None) == ""
    assert data_livre_para_banco("16/11/2023") == "2023-11-16"
    assert data_livre_para_banco(" - ") == "-"
    assert data_livre_para_banco("") is None


def test_calendario_da_data_de_compra(janela):
    aba = janela.aba_instrumentos
    edicao = aba.criar_janela_edicao(aba.repo.listar_instrumentos()[0])
    assert edicao.campos["data_compra"].text() == "16/11/2023"
    assert not edicao.tem_alteracao()  # só mostrar em dd/mm/aaaa não é alteração
    edicao.calendario_compra.abrir()
    assert edicao.calendario_compra.calendario.selectedDate() == QDate(2023, 11, 16)
    edicao.calendario_compra._escolheu(QDate(2024, 2, 5))
    assert edicao.campos["data_compra"].text() == "05/02/2024"
    edicao.salvar_instrumento()
    salvo = aba.repo.obter_instrumento(edicao.instrumento.id)
    assert salvo.data_compra == "2024-02-05"
    assert aba.valores["data_compra"].text() == "<b>05/02/2024</b>"
