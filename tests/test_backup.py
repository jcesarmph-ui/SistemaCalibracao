"""Backup diário automático do banco."""

import sqlite3
from datetime import date, timedelta

import pytest

from calibracao.dados.backup import fazer_backup_diario
from calibracao.dados.esquema import conectar, criar_tabelas


@pytest.fixture
def banco(tmp_path):
    caminho = tmp_path / "calibracao.db"
    conexao = conectar(caminho)
    criar_tabelas(conexao)
    conexao.execute("INSERT INTO instrumentos (codigo, tipo) VALUES ('X-1', 'Trena')")
    conexao.commit()
    conexao.close()
    return caminho


def test_copia_do_dia_com_os_dados(banco):
    copia = fazer_backup_diario(banco, date(2027, 3, 15))
    assert copia == banco.parent / "backup" / "calibracao_2027-03-15.db"
    conexao = sqlite3.connect(copia)
    assert conexao.execute("SELECT codigo FROM instrumentos").fetchone()[0] == "X-1"
    conexao.close()


def test_uma_copia_por_dia(banco):
    assert fazer_backup_diario(banco, date(2027, 3, 15)) is not None
    assert fazer_backup_diario(banco, date(2027, 3, 15)) is None  # abriu de novo no mesmo dia


def test_guarda_so_as_mais_recentes(banco):
    inicio = date(2027, 1, 1)
    for dia in range(35):
        fazer_backup_diario(banco, inicio + timedelta(days=dia), manter=30)
    copias = sorted((banco.parent / "backup").glob("*.db"))
    assert len(copias) == 30
    assert copias[0].name == "calibracao_2027-01-06.db"  # os 5 primeiros dias foram apagados
    assert copias[-1].name == "calibracao_2027-02-04.db"


def test_nao_apaga_outros_arquivos_da_pasta(banco):
    pasta = banco.parent / "backup"
    pasta.mkdir()
    manual = pasta / "calibracao_antes_da_mudanca.db"
    manual.write_bytes(b"copia feita a mao")
    for dia in range(3):
        fazer_backup_diario(banco, date(2027, 1, 1) + timedelta(days=dia), manter=1)
    assert manual.exists()
