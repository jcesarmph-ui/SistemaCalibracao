"""Estrutura do banco: criação do zero e atualização do banco gerado pelo importador (versão 1)."""

import pytest

from calibracao.dados.esquema import TABELAS, VERSAO_ESQUEMA, conectar, criar_tabelas, versao


def test_banco_novo_na_versao_atual(tmp_path):
    conexao = conectar(tmp_path / "novo.db")
    criar_tabelas(conexao)
    assert versao(conexao) == VERSAO_ESQUEMA == 2
    tabelas = {linha[0] for linha in conexao.execute("SELECT name FROM sqlite_master")}
    assert {"calibracoes", "pontos_calibracao", "desativacoes"} <= tabelas


def test_nunca_usa_wal(tmp_path):
    # WAL não funciona em pasta de rede.
    conexao = conectar(tmp_path / "rede.db")
    assert conexao.execute("PRAGMA journal_mode").fetchone()[0] == "delete"


def test_atualiza_banco_da_versao_1_sem_perder_dados(tmp_path):
    conexao = conectar(tmp_path / "v1.db")
    conexao.executescript(TABELAS)  # banco como o importador gerava
    conexao.execute("INSERT INTO metadados VALUES ('versao_esquema', '1')")
    conexao.execute("INSERT INTO instrumentos (codigo, tipo) VALUES ('PAQ-999', 'Paquímetro')")
    conexao.commit()

    criar_tabelas(conexao)
    criar_tabelas(conexao)  # rodar de novo não estraga nada

    assert versao(conexao) == 2
    linha = conexao.execute("SELECT codigo, exige_calibracao FROM instrumentos").fetchone()
    assert tuple(linha) == ("PAQ-999", 1)  # todos continuam exigindo calibração


def test_recusa_banco_de_versao_mais_nova(tmp_path):
    conexao = conectar(tmp_path / "futuro.db")
    criar_tabelas(conexao)
    conexao.execute("UPDATE metadados SET valor = '99' WHERE chave = 'versao_esquema'")
    with pytest.raises(RuntimeError, match="mais nova"):
        criar_tabelas(conexao)


def test_apagar_calibracao_apaga_os_pontos_medidos(tmp_path):
    conexao = conectar(tmp_path / "cascata.db")
    criar_tabelas(conexao)
    conexao.execute("INSERT INTO instrumentos (id, codigo, tipo) VALUES (1, 'X-1', 'X')")
    conexao.execute("""INSERT INTO calibracoes (id, instrumento_id, data_calibracao, resultado)
                       VALUES (1, 1, '2027-03-10', 'Aprovado')""")
    conexao.execute("""INSERT INTO pontos_calibracao (calibracao_id, ordem, tipo, descricao,
                       resultado) VALUES (1, 1, 'NUMERICO', '10', 'Aprovado')""")
    conexao.execute("DELETE FROM calibracoes WHERE id = 1")
    assert conexao.execute("SELECT COUNT(*) FROM pontos_calibracao").fetchone()[0] == 0
