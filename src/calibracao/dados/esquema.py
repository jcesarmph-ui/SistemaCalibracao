"""Tabelas do banco SQLite, abertura da conexão e atualização de bancos antigos.

Exclusão é lógica: `excluido_em` preenchido = registro na Lixeira.
Versão 1: cadastro (instrumentos, planos e pontos) — é a do banco gerado pelo importador.
Versão 2: calibrações com os pontos medidos, desativação de instrumentos e "não precisa de
calibração".
Versão 3: condição do instrumento (Em uso / Orientação indicativa / Desativado) com histórico, no
lugar das desativações; parecer final e custo da calibração; custo de compra e responsável do
instrumento.
Versão 4: trava de edição para uso em rede (uma linha só: quem está editando).
"""

import sqlite3
from pathlib import Path

VERSAO_ESQUEMA = 5

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

TABELAS_V2 = """
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
"""

# Versão 3. A condição atual é a da mudança mais recente (data, depois ordem de registro); sem
# nenhuma mudança, o instrumento está "Em uso". Mudança feita por uma calibração guarda o
# `calibracao_id`: se a calibração for para a Lixeira, a mudança deixa de valer.
TABELAS_V3 = """
CREATE TABLE IF NOT EXISTS condicoes (
    id INTEGER PRIMARY KEY,
    instrumento_id INTEGER NOT NULL REFERENCES instrumentos(id),
    condicao TEXT NOT NULL
        CHECK (condicao IN ('Em uso', 'Orientação indicativa', 'Desativado')),
    data TEXT NOT NULL,
    motivo TEXT,
    calibracao_id INTEGER REFERENCES calibracoes(id) ON DELETE CASCADE,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_condicoes_instrumento ON condicoes(instrumento_id);
"""

# Versão 4. No máximo uma linha: quem está editando agora (ver `calibracao.regras.trava`).
TABELAS_V4 = """
CREATE TABLE IF NOT EXISTS trava_edicao (
    id INTEGER PRIMARY KEY CHECK (id = 1),
    token TEXT NOT NULL,
    usuario TEXT NOT NULL,
    computador TEXT NOT NULL,
    desde TEXT NOT NULL,
    ultimo_sinal TEXT NOT NULL,
    sinal INTEGER NOT NULL,
    -- quem, no modo consulta, pediu para editar (quem edita recebe o aviso para liberar)
    pedido_usuario TEXT,
    pedido_computador TEXT,
    pedido_em TEXT
);
"""

# Versão 5. Cada correção de uma calibração já salva: quando, quem (usuário do Windows) e o que
# mudou, uma linha "antes → depois" por campo (pedido do usuário em 2026-10-30).
TABELAS_V5 = """
CREATE TABLE IF NOT EXISTS correcoes_calibracao (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    calibracao_id INTEGER NOT NULL REFERENCES calibracoes(id) ON DELETE CASCADE,
    quando TEXT NOT NULL,
    usuario TEXT NOT NULL,
    mudancas TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_correcoes_calibracao ON correcoes_calibracao(calibracao_id);
"""

# Colunas acrescentadas na versão 3: (tabela, coluna, tipo).
COLUNAS_V3 = [
    ("instrumentos", "custo_compra", "REAL"),
    ("instrumentos", "responsavel", "TEXT"),
    ("calibracoes", "parecer_final", "TEXT"),
    ("calibracoes", "motivo_parecer", "TEXT"),
    ("calibracoes", "custo_calibracao", "REAL"),
]


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
    conexao.executescript(TABELAS_V3)
    for tabela, coluna, tipo in COLUNAS_V3:
        if coluna not in _colunas(conexao, tabela):
            conexao.execute(f"ALTER TABLE {tabela} ADD COLUMN {coluna} {tipo}")
    _migrar_desativacoes(conexao)
    conexao.executescript(TABELAS_V4)
    for coluna in ("pedido_usuario", "pedido_computador", "pedido_em"):
        if coluna not in _colunas(conexao, "trava_edicao"):
            conexao.execute(f"ALTER TABLE trava_edicao ADD COLUMN {coluna} TEXT")
    conexao.executescript(TABELAS_V5)
    conexao.execute(
        "INSERT OR REPLACE INTO metadados (chave, valor) VALUES ('versao_esquema', ?)",
        (str(VERSAO_ESQUEMA),),
    )


def _migrar_desativacoes(conexao: sqlite3.Connection) -> None:
    """Banco da versão 2: cada desativação vira "Desativado" e a reativação vira "Em uso"."""
    if not _colunas(conexao, "desativacoes"):
        return
    for linha in conexao.execute("SELECT * FROM desativacoes ORDER BY data, id").fetchall():
        conexao.execute(
            "INSERT INTO condicoes (instrumento_id, condicao, data, motivo) "
            "VALUES (?, 'Desativado', ?, ?)",
            (linha["instrumento_id"], linha["data"], linha["motivo"]),
        )
        if linha["reativado_em"]:
            conexao.execute(
                "INSERT INTO condicoes (instrumento_id, condicao, data) VALUES (?, 'Em uso', ?)",
                (linha["instrumento_id"], linha["reativado_em"]),
            )
    conexao.execute("DROP TABLE desativacoes")
