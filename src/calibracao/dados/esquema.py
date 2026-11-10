"""Tabelas do banco SQLite, abertura da conexão e atualização de bancos antigos.

Exclusão é lógica: `excluido_em` preenchido = registro na Lixeira.
Versão 1: cadastro (instrumentos, planos e pontos) — é a do banco gerado pelo importador.
Versão 2: calibrações com os pontos medidos, desativação de instrumentos e "não precisa de
calibração".
Versão 3: condição do instrumento (Em uso / Orientação indicativa / Desativado) com histórico, no
lugar das desativações; parecer final e custo da calibração; custo de compra e responsável do
instrumento.
Versão 4: trava de edição para uso em rede (uma linha só: quem está editando).
Versão 5: registro das correções de calibrações. Versão 6: motivo do atraso.
Versão 7: orientação indicativa deixa de ser condição (pedido de 2026-11-03): vira marca na
localização, com histórico próprio (`marcas_indicativa`).
Versão 8: data prevista da 1ª calibração no programa, digitada na ficha olhando a DQ05 (pedido de
2026-11-03): o programa não guarda as calibrações antigas da planilha, só essa data.
Versão 9: ponto com "U não se aplica" (na DQ05, "-" ou "N/A" onde vai a incerteza), no plano e na
"foto" guardada com cada calibração.
Sem mudar a versão (2026-11-10): tipos e locais com um nome só (`_unificar_nomes`), uma vez, marcado
em `metadados.nomes_unificados` — o banco continua abrindo na versão anterior do programa.
"""

import sqlite3
from pathlib import Path

from calibracao.regras.localizacao import com_marcas
from calibracao.regras.padronizacao import (
    localizacao_padrao,
    preferidas_dos_locais,
    preferidas_dos_tipos,
    tipo_juntado,
    tipo_padrao,
)

VERSAO_ESQUEMA = 9

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

# Versão 7. Histórico da marca de orientação indicativa (a marca em si é o " - Orientação
# indicativa" da localização). Linha de uma calibração na Lixeira deixa de valer, como nas
# condições; `calibracao_id` preenchido = veio do parecer final.
# PDF do certificado de cada calibração (pedido de 2026-11-10), sem mudar a versão do esquema: a
# versão anterior do programa abre o banco e só não vê esta tabela. O arquivo fica na pasta
# `certificados/` ao lado do banco; aqui, a ligação e a conferência (SHA-256).
TABELA_CERTIFICADOS = """
CREATE TABLE IF NOT EXISTS certificados (
    id INTEGER PRIMARY KEY,
    calibracao_id INTEGER NOT NULL REFERENCES calibracoes(id),
    arquivo TEXT NOT NULL,          -- nome dentro da pasta certificados/
    nome_original TEXT NOT NULL,    -- nome do arquivo que a pessoa escolheu
    tamanho INTEGER NOT NULL,
    sha256 TEXT NOT NULL,
    enviado_em TEXT NOT NULL,
    enviado_por TEXT,               -- "usuário - PC"
    excluido_em TEXT,
    motivo_exclusao TEXT
);
CREATE INDEX IF NOT EXISTS certificados_da_calibracao ON certificados(calibracao_id);
"""

# Painel de indicadores montado pelo usuário (pedido de 2026-11-10), sem mudar a versão do
# esquema. Um painel só para todos; cada gráfico guarda a definição (JSON de
# `regras.indicadores.DefinicaoGrafico`). Tirar = `excluido_em` (o "desfazer" volta).
TABELA_PAINEL = """
CREATE TABLE IF NOT EXISTS graficos_painel (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    definicao TEXT NOT NULL,
    criado_em TEXT NOT NULL,
    excluido_em TEXT
);
"""

# Relatórios finais guardados (pedido de 2026-11-10), sem mudar a versão do esquema: um por
# mês que acabou e um por ano que acabou. O PDF fica em `relatorios/` ao lado do banco.
TABELA_RELATORIOS = """
CREATE TABLE IF NOT EXISTS relatorios (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    periodo TEXT NOT NULL UNIQUE,   -- "2027-10" (mês) ou "2027" (ano)
    arquivo TEXT NOT NULL,          -- nome dentro da pasta relatorios/
    sha256 TEXT NOT NULL,
    gerado_em TEXT NOT NULL,
    gerado_por TEXT
);
"""

TABELAS_V7 = """
CREATE TABLE IF NOT EXISTS marcas_indicativa (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    instrumento_id INTEGER NOT NULL REFERENCES instrumentos(id),
    marcada INTEGER NOT NULL,
    data TEXT NOT NULL,
    motivo TEXT,
    calibracao_id INTEGER REFERENCES calibracoes(id) ON DELETE CASCADE,
    criado_em TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);
CREATE INDEX IF NOT EXISTS ix_marcas_indicativa_instrumento ON marcas_indicativa(instrumento_id);
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
    # Versão 6: motivo de a calibração ter sido feita depois do mês previsto (opcional).
    if "motivo_atraso" not in _colunas(conexao, "calibracoes"):
        conexao.execute("ALTER TABLE calibracoes ADD COLUMN motivo_atraso TEXT")
    # ...e, enquanto ainda não foi feita (vencida), o motivo informado no instrumento.
    if "motivo_atraso_pendente" not in _colunas(conexao, "instrumentos"):
        conexao.execute("ALTER TABLE instrumentos ADD COLUMN motivo_atraso_pendente TEXT")
    conexao.executescript(TABELAS_V7)
    conexao.executescript(TABELA_CERTIFICADOS)
    conexao.executescript(TABELA_PAINEL)
    conexao.executescript(TABELA_RELATORIOS)
    _painel_inicial(conexao)
    if "primeira_prevista" not in _colunas(conexao, "instrumentos"):
        conexao.execute("ALTER TABLE instrumentos ADD COLUMN primeira_prevista TEXT")
    for tabela in ("pontos_plano", "pontos_calibracao"):
        if "incerteza_nao_aplica" not in _colunas(conexao, tabela):
            conexao.execute(f"ALTER TABLE {tabela} ADD COLUMN incerteza_nao_aplica "
                            "INTEGER NOT NULL DEFAULT 0")
    _migrar_condicao_indicativa(conexao)
    _unificar_nomes(conexao)
    conexao.execute(
        "INSERT OR REPLACE INTO metadados (chave, valor) VALUES ('versao_esquema', ?)",
        (str(VERSAO_ESQUEMA),),
    )


def _unificar_nomes(conexao: sqlite3.Connection) -> None:
    """Uma vez por banco (pedido de 2026-11-10): tipos e locais que só mudam nas maiúsculas ficam
    com a grafia da maioria, "Régua graduada para furos" vira "Régua graduada" e cada local de
    "Serralheria / Manutenção" fica com o nome que os outros instrumentos usam."""
    feito = conexao.execute(
        "SELECT 1 FROM metadados WHERE chave = 'nomes_unificados'").fetchone()
    if feito:
        return
    linhas = conexao.execute(
        "SELECT id, tipo, localizacao, observacoes FROM instrumentos").fetchall()
    tipos = preferidas_dos_tipos(linha["tipo"] for linha in linhas)
    locais = preferidas_dos_locais(linha["localizacao"] for linha in linhas)
    for linha in linhas:
        tipo = tipo_padrao(linha["tipo"], tipos)
        local = localizacao_padrao(linha["localizacao"], locais)
        observacoes = linha["observacoes"]
        if tipo_juntado(linha["tipo"]):  # o nome antigo (ex.: o modelo da balança) não se perde
            nota = f"Tipo antes da unificação: {linha['tipo']}"
            observacoes = f"{observacoes} | {nota}" if observacoes else nota
        if (tipo, local, observacoes) != (linha["tipo"], linha["localizacao"],
                                          linha["observacoes"]):
            conexao.execute("UPDATE instrumentos SET tipo = ?, localizacao = ?, observacoes = ? "
                            "WHERE id = ?", (tipo, local, observacoes, linha["id"]))
    conexao.execute("INSERT INTO metadados (chave, valor) VALUES ('nomes_unificados', '1')")


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


def _migrar_condicao_indicativa(conexao: sqlite3.Connection) -> None:
    """Banco até a versão 6: a condição "Orientação indicativa" vira "Em uso" + marca.

    Cada mudança para orientação indicativa vira uma linha no histórico da marca; quem estava
    nessa condição ganha o " - Orientação indicativa" na localização.
    """
    linhas = conexao.execute(
        "SELECT * FROM condicoes WHERE condicao = 'Orientação indicativa' ORDER BY id").fetchall()
    if not linhas:
        return
    validas = """SELECT k.* FROM condicoes k LEFT JOIN calibracoes c ON c.id = k.calibracao_id
                 WHERE k.calibracao_id IS NULL OR c.excluido_em IS NULL"""
    atuais = {linha["instrumento_id"]: linha["condicao"] for linha in conexao.execute(
        f"{validas} ORDER BY k.data, k.id")}
    for linha in linhas:
        conexao.execute(
            "INSERT INTO marcas_indicativa (instrumento_id, marcada, data, motivo, calibracao_id) "
            "VALUES (?, 1, ?, ?, ?)",
            (linha["instrumento_id"], linha["data"], linha["motivo"], linha["calibracao_id"]))
    for instrumento_id, condicao in atuais.items():
        if condicao == "Orientação indicativa":
            local = conexao.execute("SELECT localizacao FROM instrumentos WHERE id = ?",
                                    (instrumento_id,)).fetchone()[0]
            conexao.execute("UPDATE instrumentos SET localizacao = ? WHERE id = ?",
                            (com_marcas(local, indicativa=True), instrumento_id))
    conexao.execute("UPDATE condicoes SET condicao = 'Em uso' "
                    "WHERE condicao = 'Orientação indicativa'")


def _painel_inicial(conexao: sqlite3.Connection) -> None:
    """Na 1ª vez, o painel começa com os gráficos escolhidos pelo usuário (uma vez só: se ele
    tirar todos, o painel fica vazio — marcado em `metadados`)."""
    import datetime

    from calibracao.regras.indicadores import PAINEL_INICIAL

    if conexao.execute("SELECT 1 FROM metadados WHERE chave = 'painel_iniciado'").fetchone():
        return
    agora = datetime.datetime.now().isoformat(timespec="seconds")
    for definicao in PAINEL_INICIAL:
        conexao.execute("INSERT INTO graficos_painel (definicao, criado_em) VALUES (?, ?)",
                        (definicao.para_json(), agora))
    conexao.execute("INSERT INTO metadados (chave, valor) VALUES ('painel_iniciado', 'sim')")
