import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent.parent.parent
DATA_DIR = BASE_DIR / "data"
DATABASE = DATA_DIR / "calibracao.db"


def conectar():
    DATA_DIR.mkdir(exist_ok=True)

    conexao = sqlite3.connect(DATABASE)
    conexao.row_factory = sqlite3.Row

    return conexao


def criar_banco():
    conexao = conectar()

    cursor = conexao.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            codigo TEXT NOT NULL UNIQUE,
            descricao TEXT NOT NULL,
            fabricante TEXT,
            modelo TEXT,
            numero_serie TEXT,
            localizacao TEXT,
            responsavel TEXT,
            periodicidade_meses INTEGER,
            status TEXT NOT NULL DEFAULT 'Ativo',
            observacoes TEXT,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conexao.commit()
    conexao.close()