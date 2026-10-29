"""Tabelas do banco SQLite, abertura da conexão e atualização de bancos antigos.

Exclusão é lógica: `excluido_em` preenchido = registro na Lixeira.
Versão 1: cadastro (instrumentos, planos e pontos) — é a do banco gerado pelo importador.
Versão 2: calibrações com os pontos medidos, desativação de instrumentos e "não precisa de
calibração".
"""

import sqlite3
from pathlib import Path

VERSAO_ESQUEMA = 2

TABELAS = """
CREATE TABLE IF NOT EXISTS metadados (
    chave TEXT PRIMARY KEY,
    valor TEXT
);

CREATE TABLE IF NOT EXISTS planos (
    id INTEGER PRIMARY KEY,
    nome TEXT NOT NULL,
    observacoes TEXT,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    excluido_em TEXT,
    motivo_exclusao TEXT
);

CREATE TABLE IF NOT EXISTS instrumentos (
    id INTEGER PRIMARY KEY,
    codigo TEXT NOT NULL UNIQUE,
    tipo TEXT NOT NULL,
    localizacao TEXT,
    faixa TEXT,
    resolucao TEXT,
    fabricante TEXT,
    data_compra TEXT,
    periodicidade_meses INTEGER,
    plano_id INTEGER REFERENCES planos(id),
    exige_calibracao INTEGER NOT NULL DEFAULT 1,
    observacoes TEXT,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    excluido_em TEXT,
    motivo_exclusao TEXT
);

-- tipo: NUMERICO (nominal ± tolerância), LIMITE (mínimo/máximo), CLASSE (classe exigida),
--       CRITERIO (texto a atender, ex.: "Executa função"), VERIFICACAO (item a conferir, ex.: OK)
CREATE TABLE IF NOT EXISTS pontos_plano (
    id INTEGER PRIMARY KEY,
    plano_id INTEGER NOT NULL REFERENCES planos(id),
    ordem INTEGER NOT NULL,
    ordem_original TEXT,
    secao TEXT,
    tipo TEXT NOT NULL
        CHECK (tipo IN ('NUMERICO', 'LIMITE', 'CLASSE', 'CRITERIO', 'VERIFICACAO')),
    descricao TEXT NOT NULL,
    valor_nominal REAL,
    unidade TEXT,
    tolerancia_inferior REAL,
    tolerancia_superior REAL,
    valor_minimo REAL,
    valor_maximo REAL,
    classe_exigida TEXT,
    criterio TEXT,
    incerteza REAL,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    excluido_em TEXT,
    motivo_exclusao TEXT
);
"""

# Versão 2. O instrumento está desativado enquanto houver uma desativação sem `reativado_em`;
# as linhas antigas ficam como histórico (desativado em X por Y, reativado em Z).
TABELAS_V2 = """
CREATE TABLE IF NOT EXISTS desativacoes (
    id INTEGER PRIMARY KEY,
    instrumento_id INTEGER NOT NULL REFERENCES instrumentos(id),
    data TEXT NOT NULL,
    motivo TEXT NOT NULL,
    reativado_em TEXT,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS calibracoes (
    id INTEGER PRIMARY KEY,
    instrumento_id INTEGER NOT NULL REFERENCES instrumentos(id),
    data_calibracao TEXT NOT NULL,
    -- periodicidade usada no cálculo, guardada para a próxima data não mudar se o cadastro mudar
    periodicidade_meses INTEGER,
    data_proxima TEXT,
    laboratorio TEXT,
    certificado TEXT,
    responsavel TEXT,
    resultado TEXT NOT NULL,
    observacoes TEXT,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    excluido_em TEXT,
    motivo_exclusao TEXT
);

-- "Foto" do ponto do plano no dia da calibração (nominal, tolerância, U…): se o plano mudar depois,
-- a calibração antiga continua mostrando o que foi usado.
CREATE TABLE IF NOT EXISTS pontos_calibracao (
    id INTEGER PRIMARY KEY,
    calibracao_id INTEGER NOT NULL REFERENCES calibracoes(id) ON DELETE CASCADE,
    ponto_plano_id INTEGER REFERENCES pontos_plano(id),
    ordem INTEGER NOT NULL,
    secao TEXT,
    tipo TEXT NOT NULL,
    descricao TEXT NOT NULL,
    valor_nominal REAL,
    unidade TEXT,
    tolerancia_inferior REAL,
    tolerancia_superior REAL,
    valor_minimo REAL,
    valor_maximo REAL,
    classe_exigida TEXT,
    criterio TEXT,
    -- medido (com nominal) ou erro do certificado (sem nominal fixo)
    valor REAL,
    incerteza REAL,
    -- só para registro, quando o certificado traz (não entram na conta)
    valor_padrao REAL,
    valor_medido REAL,
    resultado TEXT NOT NULL,
    -- obrigatório quando o resultado é "Não aplicável"
    observacao TEXT
);

CREATE INDEX IF NOT EXISTS ix_calibracoes_instrumento ON calibracoes(instrumento_id);
CREATE INDEX IF NOT EXISTS ix_pontos_calibracao ON pontos_calibracao(calibracao_id);
CREATE INDEX IF NOT EXISTS ix_desativacoes_instrumento ON desativacoes(instrumento_id);
"""


def conectar(caminho: Path) -> sqlite3.Connection:
    """Abre o banco no modo seguro para pasta de rede (journal tradicional, nunca WAL)."""
    conexao = sqlite3.connect(caminho, timeout=10)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA journal_mode = DELETE")
    conexao.execute("PRAGMA busy_timeout = 10000")
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def versao(conexao: sqlite3.Connection) -> int:
    linha = conexao.execute(
        "SELECT valor FROM metadados WHERE chave = 'versao_esquema'"
    ).fetchone()
    return int(linha[0]) if linha else 0


def _colunas(conexao: sqlite3.Connection, tabela: str) -> set[str]:
    return {linha[1] for linha in conexao.execute(f"PRAGMA table_info({tabela})")}


def criar_tabelas(conexao: sqlite3.Connection) -> None:
    """Cria o banco do zero ou atualiza um banco antigo até a versão atual (pode repetir)."""
    banco_existente = bool(_colunas(conexao, "metadados"))
    if banco_existente and versao(conexao) > VERSAO_ESQUEMA:
        raise RuntimeError("O banco é de uma versão mais nova do programa.")
    conexao.executescript(TABELAS)
    if "exige_calibracao" not in _colunas(conexao, "instrumentos"):
        conexao.execute(
            "ALTER TABLE instrumentos ADD COLUMN exige_calibracao INTEGER NOT NULL DEFAULT 1"
        )
    conexao.executescript(TABELAS_V2)
    conexao.execute(
        "INSERT OR REPLACE INTO metadados (chave, valor) VALUES ('versao_esquema', ?)",
        (str(VERSAO_ESQUEMA),),
    )
