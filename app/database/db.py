import sqlite3
from pathlib import Path


# ============================================================
# CAMINHOS
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent.parent

DATA_DIR = BASE_DIR / "data"

DATABASE = DATA_DIR / "calibracao.db"


# ============================================================
# CONEXÃO COM O BANCO
# ============================================================

def conectar():
    """
    Cria uma conexão com o banco de dados SQLite.
    """

    DATA_DIR.mkdir(exist_ok=True)

    conexao = sqlite3.connect(DATABASE)

    conexao.row_factory = sqlite3.Row

    conexao.execute("PRAGMA foreign_keys = ON")

    return conexao


# ============================================================
# CRIAÇÃO DO BANCO
# ============================================================

def criar_banco():
    """
    Cria as tabelas necessárias caso ainda não existam.
    """

    conexao = conectar()

    cursor = conexao.cursor()


    # ========================================================
    # EQUIPAMENTOS
    # ========================================================

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


    # ========================================================
    # CALIBRAÇÕES
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS calibracoes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            equipamento_id INTEGER NOT NULL,

            data_calibracao TEXT NOT NULL,

            data_proxima_calibracao TEXT,

            laboratorio TEXT,

            certificado TEXT,

            resultado TEXT,

            observacoes TEXT,

            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (equipamento_id)
                REFERENCES equipamentos(id)
                ON DELETE CASCADE
        )
    """)


    # ========================================================
    # PONTOS DE CALIBRAÇÃO
    # ========================================================

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pontos_calibracao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            calibracao_id INTEGER NOT NULL,

            ponto_nominal REAL NOT NULL,

            valor_encontrado REAL,

            unidade TEXT,

            tolerancia_inferior REAL,

            tolerancia_superior REAL,

            resultado TEXT,

            observacoes TEXT,

            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (calibracao_id)
                REFERENCES calibracoes(id)
                ON DELETE CASCADE
        )
    """)


    # ========================================================
    # FINALIZAÇÃO
    # ========================================================

    conexao.commit()

    conexao.close()