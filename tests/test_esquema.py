"""Estrutura do banco: criação do zero e atualização de bancos antigos (versões 1 e 2)."""

import pytest

from calibracao.dados.esquema import TABELAS, VERSAO_ESQUEMA, conectar, criar_tabelas, versao


def test_banco_novo_na_versao_atual(tmp_path):
    conexao = conectar(tmp_path / "novo.db")
    criar_tabelas(conexao)
    assert versao(conexao) == VERSAO_ESQUEMA == 4
    tabelas = {linha[0] for linha in conexao.execute("SELECT name FROM sqlite_master")}
    assert {"calibracoes", "pontos_calibracao", "condicoes", "trava_edicao"} <= tabelas
    assert "desativacoes" not in tabelas


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

    assert versao(conexao) == 4
    linha = conexao.execute("SELECT codigo, exige_calibracao FROM instrumentos").fetchone()
    assert tuple(linha) == ("PAQ-999", 1)  # todos continuam exigindo calibração


def test_atualiza_banco_da_versao_2_levando_as_desativacoes(tmp_path):
    conexao = conectar(tmp_path / "v2.db")
    conexao.executescript(TABELAS)
    conexao.executescript("""
        CREATE TABLE desativacoes (id INTEGER PRIMARY KEY, instrumento_id INTEGER NOT NULL,
            data TEXT NOT NULL, motivo TEXT NOT NULL, reativado_em TEXT,
            criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP);
        INSERT INTO metadados VALUES ('versao_esquema', '2');
        INSERT INTO instrumentos (id, codigo, tipo) 
            VALUES (1, 'TRE-1', 'Trena'), (2, 'TRE-2', 'Trena');
        INSERT INTO desativacoes (instrumento_id, data, motivo, reativado_em)
            VALUES (1, '2027-01-10', 'Perdido', '2027-02-05'), (2, '2027-03-01', 'Quebrou', NULL);
    """)
    conexao.commit()

    criar_tabelas(conexao)
    criar_tabelas(conexao)

    historico = [tuple(linha) for linha in conexao.execute(
        "SELECT instrumento_id, condicao, data, motivo FROM condicoes ORDER BY id")]
    assert historico == [
        (1, "Desativado", "2027-01-10", "Perdido"),
        (1, "Em uso", "2027-02-05", None),
        (2, "Desativado", "2027-03-01", "Quebrou"),
    ]
    colunas = {linha[1] for linha in conexao.execute("PRAGMA table_info(calibracoes)")}
    assert {"parecer_final", "motivo_parecer", "custo_calibracao"} <= colunas


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
