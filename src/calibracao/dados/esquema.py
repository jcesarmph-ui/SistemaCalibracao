"""Tabelas do banco SQLite e abertura da conexão.

Por enquanto só o cadastro (instrumentos, planos e pontos); as calibrações entram na fase 2.
Exclusão é lógica: `excluido_em` preenchido = registro na Lixeira.
"""

import sqlite3
from pathlib import Path

VERSAO_ESQUEMA = 1

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


def conectar(caminho: Path) -> sqlite3.Connection:
    """Abre o banco no modo seguro para pasta de rede (journal tradicional, nunca WAL)."""
    conexao = sqlite3.connect(caminho, timeout=10)
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA journal_mode = DELETE")
    conexao.execute("PRAGMA busy_timeout = 10000")
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao


def criar_tabelas(conexao: sqlite3.Connection) -> None:
    conexao.executescript(TABELAS)
    conexao.execute(
        "INSERT OR REPLACE INTO metadados (chave, valor) VALUES ('versao_esquema', ?)",
        (str(VERSAO_ESQUEMA),),
    )
