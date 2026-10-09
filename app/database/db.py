import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parents[2]
DATA_DIR = BASE_DIR / "data"
DB_PATH = DATA_DIR / "calibracao.db"


def conectar():
    DATA_DIR.mkdir(parents=True, exist_ok=True)

    conexao = sqlite3.connect(
        DB_PATH,
        timeout=30,
        check_same_thread=False
    )

    conexao.row_factory = sqlite3.Row

    conexao.execute("PRAGMA foreign_keys = ON")
    conexao.execute("PRAGMA busy_timeout = 30000")

    return conexao


def _colunas_tabela(conexao, tabela):
    resultado = conexao.execute(
        f"PRAGMA table_info({tabela})"
    ).fetchall()

    return {linha["name"] for linha in resultado}


def _adicionar_coluna_se_nao_existir(
    conexao,
    tabela,
    coluna,
    definicao,
    preenchimento=None
):
    colunas = _colunas_tabela(
        conexao,
        tabela
    )

    if coluna in colunas:
        return

    # SQLite não permite:
    #
    # ALTER TABLE ... ADD COLUMN
    # ... DEFAULT CURRENT_TIMESTAMP
    #
    # Portanto, quando existe um default dinâmico,
    # criamos a coluna sem ele e preenchemos os
    # registros existentes separadamente.

    definicao_alterada = definicao

    if "DEFAULT CURRENT_TIMESTAMP" in definicao.upper():
        definicao_alterada = (
            definicao
            .replace(
                "DEFAULT CURRENT_TIMESTAMP",
                ""
            )
            .replace(
                "default current_timestamp",
                ""
            )
            .strip()
        )

    conexao.execute(
        f"""
        ALTER TABLE {tabela}
        ADD COLUMN {coluna} {definicao_alterada}
        """
    )

    if preenchimento:
        conexao.execute(
            f"""
            UPDATE {tabela}
            SET {coluna} = {preenchimento}
            WHERE {coluna} IS NULL
            """
        )


def _expressao_coluna(
    colunas_antigas,
    coluna_nova,
    alternativas=None,
    padrao="NULL"
):
    alternativas = alternativas or []

    if coluna_nova in colunas_antigas:

        partes = [coluna_nova]

        for coluna in alternativas:
            if coluna in colunas_antigas:
                partes.append(coluna)

        if len(partes) > 1:
            return (
                "COALESCE("
                + ", ".join(partes)
                + ")"
            )

        return coluna_nova

    for coluna in alternativas:
        if coluna in colunas_antigas:
            return coluna

    return padrao


def _migrar_pontos_plano(conexao):
    """
    Migra versões antigas de pontos_plano que utilizavam
    ponto_nominal para a estrutura atual com valor_nominal.
    """

    tabela_existe = conexao.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'pontos_plano'
        """
    ).fetchone()

    if not tabela_existe:
        return

    colunas = _colunas_tabela(
        conexao,
        "pontos_plano"
    )

    if "ponto_nominal" not in colunas:
        return

    conexao.execute(
        """
        ALTER TABLE pontos_plano
        RENAME TO pontos_plano_antigo
        """
    )

    conexao.execute(
        """
        CREATE TABLE pontos_plano (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            plano_id INTEGER NOT NULL,
            ordem INTEGER NOT NULL,
            ordem_original TEXT,
            tipo_ponto TEXT NOT NULL DEFAULT 'NUMERICO',
            secao TEXT,
            descricao TEXT,
            valor_nominal REAL,
            unidade TEXT,
            tolerancia_inferior REAL,
            tolerancia_superior REAL,
            criterio TEXT,
            valor_minimo REAL,
            valor_maximo REAL,
            classe_exigida TEXT,
            entrada_tipo TEXT NOT NULL DEFAULT 'NUMERICA',
            ativo INTEGER NOT NULL DEFAULT 1,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (plano_id)
                REFERENCES planos_calibracao(id)
        )
        """
    )

    antigas = _colunas_tabela(
        conexao,
        "pontos_plano_antigo"
    )

    campos = [
        "id",
        "plano_id",
        "ordem",
        "ordem_original",
        "tipo_ponto",
        "secao",
        "descricao",
        "valor_nominal",
        "unidade",
        "tolerancia_inferior",
        "tolerancia_superior",
        "criterio",
        "valor_minimo",
        "valor_maximo",
        "classe_exigida",
        "entrada_tipo",
        "ativo",
        "criado_em"
    ]

    expressoes = [
        "id",
        "plano_id",
        (
            "ordem"
            if "ordem" in antigas
            else "rowid"
        ),
        _expressao_coluna(
            antigas,
            "ordem_original"
        ),
        _expressao_coluna(
            antigas,
            "tipo_ponto",
            padrao="'NUMERICO'"
        ),
        _expressao_coluna(
            antigas,
            "secao"
        ),
        _expressao_coluna(
            antigas,
            "descricao"
        ),
        _expressao_coluna(
            antigas,
            "valor_nominal",
            alternativas=["ponto_nominal"]
        ),
        _expressao_coluna(
            antigas,
            "unidade"
        ),
        _expressao_coluna(
            antigas,
            "tolerancia_inferior"
        ),
        _expressao_coluna(
            antigas,
            "tolerancia_superior"
        ),
        _expressao_coluna(
            antigas,
            "criterio"
        ),
        _expressao_coluna(
            antigas,
            "valor_minimo"
        ),
        _expressao_coluna(
            antigas,
            "valor_maximo"
        ),
        _expressao_coluna(
            antigas,
            "classe_exigida"
        ),
        _expressao_coluna(
            antigas,
            "entrada_tipo",
            padrao="'NUMERICA'"
        ),
        _expressao_coluna(
            antigas,
            "ativo",
            padrao="1"
        ),
        _expressao_coluna(
            antigas,
            "criado_em",
            padrao="CURRENT_TIMESTAMP"
        )
    ]

    conexao.execute(
        f"""
        INSERT INTO pontos_plano (
            {", ".join(campos)}
        )
        SELECT
            {", ".join(expressoes)}
        FROM pontos_plano_antigo
        """
    )

    conexao.execute(
        """
        DROP TABLE pontos_plano_antigo
        """
    )


def _migrar_pontos_calibracao(conexao):
    """
    Migra versões antigas de pontos_calibracao que possuíam
    ponto_nominal NOT NULL.

    A estrutura atual utiliza valor_nominal.
    """

    tabela_existe = conexao.execute(
        """
        SELECT name
        FROM sqlite_master
        WHERE type = 'table'
          AND name = 'pontos_calibracao'
        """
    ).fetchone()

    if not tabela_existe:
        return

    colunas = _colunas_tabela(
        conexao,
        "pontos_calibracao"
    )

    if "ponto_nominal" not in colunas:
        return

    conexao.execute(
        """
        ALTER TABLE pontos_calibracao
        RENAME TO pontos_calibracao_antigo
        """
    )

    conexao.execute(
        """
        CREATE TABLE pontos_calibracao (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            calibracao_id INTEGER NOT NULL,
            ponto_plano_id INTEGER,
            ordem INTEGER NOT NULL,
            ordem_original TEXT,
            tipo_ponto TEXT NOT NULL DEFAULT 'NUMERICO',
            descricao TEXT,
            valor_nominal REAL,
            valor_encontrado REAL,
            unidade TEXT,
            tolerancia_inferior REAL,
            tolerancia_superior REAL,
            criterio TEXT,
            valor_minimo REAL,
            valor_maximo REAL,
            classe_exigida TEXT,
            resultado TEXT,
            observacoes TEXT,
            criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (calibracao_id)
                REFERENCES calibracoes(id),
            FOREIGN KEY (ponto_plano_id)
                REFERENCES pontos_plano(id)
        )
        """
    )

    antigas = _colunas_tabela(
        conexao,
        "pontos_calibracao_antigo"
    )

    campos = [
        "id",
        "calibracao_id",
        "ponto_plano_id",
        "ordem",
        "ordem_original",
        "tipo_ponto",
        "descricao",
        "valor_nominal",
        "valor_encontrado",
        "unidade",
        "tolerancia_inferior",
        "tolerancia_superior",
        "criterio",
        "valor_minimo",
        "valor_maximo",
        "classe_exigida",
        "resultado",
        "observacoes",
        "criado_em"
    ]

    expressoes = [
        "id",
        "calibracao_id",
        _expressao_coluna(
            antigas,
            "ponto_plano_id"
        ),
        (
            "ordem"
            if "ordem" in antigas
            else "rowid"
        ),
        _expressao_coluna(
            antigas,
            "ordem_original"
        ),
        _expressao_coluna(
            antigas,
            "tipo_ponto",
            padrao="'NUMERICO'"
        ),
        _expressao_coluna(
            antigas,
            "descricao"
        ),
        _expressao_coluna(
            antigas,
            "valor_nominal",
            alternativas=["ponto_nominal"]
        ),
        _expressao_coluna(
            antigas,
            "valor_encontrado",
            alternativas=[
                "valor_medido",
                "valor_obtido"
            ]
        ),
        _expressao_coluna(
            antigas,
            "unidade"
        ),
        _expressao_coluna(
            antigas,
            "tolerancia_inferior"
        ),
        _expressao_coluna(
            antigas,
            "tolerancia_superior"
        ),
        _expressao_coluna(
            antigas,
            "criterio"
        ),
        _expressao_coluna(
            antigas,
            "valor_minimo"
        ),
        _expressao_coluna(
            antigas,
            "valor_maximo"
        ),
        _expressao_coluna(
            antigas,
            "classe_exigida"
        ),
        _expressao_coluna(
            antigas,
            "resultado"
        ),
        _expressao_coluna(
            antigas,
            "observacoes"
        ),
        _expressao_coluna(
            antigas,
            "criado_em",
            padrao="CURRENT_TIMESTAMP"
        )
    ]

    conexao.execute(
        f"""
        INSERT INTO pontos_calibracao (
            {", ".join(campos)}
        )
        SELECT
            {", ".join(expressoes)}
        FROM pontos_calibracao_antigo
        """
    )

    conexao.execute(
        """
        DROP TABLE pontos_calibracao_antigo
        """
    )


def criar_banco():
    DATA_DIR.mkdir(
        parents=True,
        exist_ok=True
    )

    conexao = conectar()

    try:

        conexao.execute(
            "PRAGMA foreign_keys = OFF"
        )

        # ====================================================
        # TIPOS
        # ====================================================

        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS tipos_instrumento (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                nome TEXT NOT NULL UNIQUE,
                descricao TEXT,
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP
            )
            """
        )

        # ====================================================
        # PLANOS
        # ====================================================

        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS planos_calibracao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                tipo_instrumento_id INTEGER,
                nome TEXT NOT NULL,
                faixa TEXT,
                resolucao TEXT,
                periodicidade_meses INTEGER,
                observacoes TEXT,
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tipo_instrumento_id)
                    REFERENCES tipos_instrumento(id)
            )
            """
        )

        # ====================================================
        # PONTOS DOS PLANOS
        # ====================================================

        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS pontos_plano (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                plano_id INTEGER NOT NULL,
                ordem INTEGER NOT NULL,
                ordem_original TEXT,
                tipo_ponto TEXT NOT NULL DEFAULT 'NUMERICO',
                secao TEXT,
                descricao TEXT,
                valor_nominal REAL,
                unidade TEXT,
                tolerancia_inferior REAL,
                tolerancia_superior REAL,
                criterio TEXT,
                valor_minimo REAL,
                valor_maximo REAL,
                classe_exigida TEXT,
                entrada_tipo TEXT NOT NULL DEFAULT 'NUMERICA',
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (plano_id)
                    REFERENCES planos_calibracao(id)
            )
            """
        )

        # ====================================================
        # EQUIPAMENTOS
        # ====================================================

        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS equipamentos (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                codigo TEXT NOT NULL UNIQUE,
                descricao TEXT NOT NULL,
                tipo_instrumento_id INTEGER,
                plano_id INTEGER,
                fabricante TEXT,
                modelo TEXT,
                numero_serie TEXT,
                faixa TEXT,
                resolucao TEXT,
                localizacao TEXT,
                responsavel TEXT,
                periodicidade_meses INTEGER,
                status TEXT DEFAULT 'ATIVO',
                data_ultima_calibracao TEXT,
                data_proxima_calibracao TEXT,
                observacoes TEXT,
                ativo INTEGER NOT NULL DEFAULT 1,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
                atualizado_em TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (tipo_instrumento_id)
                    REFERENCES tipos_instrumento(id),
                FOREIGN KEY (plano_id)
                    REFERENCES planos_calibracao(id)
            )
            """
        )

        # ====================================================
        # CALIBRAÇÕES
        # ====================================================

        conexao.execute(
            """
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
            )
            """
        )

        # ====================================================
        # PONTOS DE CALIBRAÇÃO
        # ====================================================

        conexao.execute(
            """
            CREATE TABLE IF NOT EXISTS pontos_calibracao (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                calibracao_id INTEGER NOT NULL,
                ponto_plano_id INTEGER,
                ordem INTEGER NOT NULL,
                ordem_original TEXT,
                tipo_ponto TEXT NOT NULL DEFAULT 'NUMERICO',
                descricao TEXT,
                valor_nominal REAL,
                valor_encontrado REAL,
                unidade TEXT,
                tolerancia_inferior REAL,
                tolerancia_superior REAL,
                criterio TEXT,
                valor_minimo REAL,
                valor_maximo REAL,
                classe_exigida TEXT,
                resultado TEXT,
                observacoes TEXT,
                criado_em TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (calibracao_id)
                    REFERENCES calibracoes(id),
                FOREIGN KEY (ponto_plano_id)
                    REFERENCES pontos_plano(id)
            )
            """
        )

        # ====================================================
        # MIGRAÇÕES IMPORTANTES
        # ====================================================

        _migrar_pontos_plano(
            conexao
        )

        _migrar_pontos_calibracao(
            conexao
        )

        # ====================================================
        # COLUNAS DE EQUIPAMENTOS
        # ====================================================

        _adicionar_coluna_se_nao_existir(
            conexao,
            "equipamentos",
            "data_ultima_calibracao",
            "TEXT"
        )

        _adicionar_coluna_se_nao_existir(
            conexao,
            "equipamentos",
            "data_proxima_calibracao",
            "TEXT"
        )

        _adicionar_coluna_se_nao_existir(
            conexao,
            "equipamentos",
            "observacoes",
            "TEXT"
        )

        _adicionar_coluna_se_nao_existir(
            conexao,
            "equipamentos",
            "ativo",
            "INTEGER NOT NULL DEFAULT 1"
        )

        _adicionar_coluna_se_nao_existir(
            conexao,
            "equipamentos",
            "criado_em",
            "TEXT",
            "CURRENT_TIMESTAMP"
        )

        _adicionar_coluna_se_nao_existir(
            conexao,
            "equipamentos",
            "atualizado_em",
            "TEXT",
            "CURRENT_TIMESTAMP"
        )

        # ====================================================
        # COLUNAS DAS CALIBRAÇÕES
        # ====================================================

        _adicionar_coluna_se_nao_existir(
            conexao,
            "calibracoes",
            "responsavel",
            "TEXT"
        )

        _adicionar_coluna_se_nao_existir(
            conexao,
            "calibracoes",
            "resultado_final",
            "TEXT"
        )

        _adicionar_coluna_se_nao_existir(
            conexao,
            "calibracoes",
            "atualizado_em",
            "TEXT",
            "CURRENT_TIMESTAMP"
        )

        # ====================================================
        # COLUNAS DOS PONTOS DO PLANO
        # ====================================================

        _adicionar_coluna_se_nao_existir(
            conexao,
            "pontos_plano",
            "valor_nominal",
            "REAL"
        )

        _adicionar_coluna_se_nao_existir(
            conexao,
            "pontos_plano",
            "valor_minimo",
            "REAL"
        )

        _adicionar_coluna_se_nao_existir(
            conexao,
            "pontos_plano",
            "valor_maximo",
            "REAL"
        )

        _adicionar_coluna_se_nao_existir(
            conexao,
            "pontos_plano",
            "classe_exigida",
            "TEXT"
        )

        _adicionar_coluna_se_nao_existir(
            conexao,
            "pontos_plano",
            "incerteza",
            "TEXT"
        )

        _adicionar_coluna_se_nao_existir(
            conexao,
            "pontos_plano",
            "entrada_tipo",
            "TEXT DEFAULT 'NUMERICA'"
        )

        _adicionar_coluna_se_nao_existir(
            conexao,
            "pontos_plano",
            "ativo",
            "INTEGER NOT NULL DEFAULT 1"
        )

        # ====================================================
        # COLUNAS DOS PONTOS DE CALIBRAÇÃO
        # ====================================================

        _adicionar_coluna_se_nao_existir(
            conexao,
            "pontos_calibracao",
            "valor_nominal",
            "REAL"
        )

        _adicionar_coluna_se_nao_existir(
            conexao,
            "pontos_calibracao",
            "valor_encontrado",
            "REAL"
        )

        _adicionar_coluna_se_nao_existir(
            conexao,
            "pontos_calibracao",
            "unidade",
            "TEXT"
        )

        _adicionar_coluna_se_nao_existir(
            conexao,
            "pontos_calibracao",
            "tolerancia_inferior",
            "REAL"
        )

        _adicionar_coluna_se_nao_existir(
            conexao,
            "pontos_calibracao",
            "tolerancia_superior",
            "REAL"
        )

        _adicionar_coluna_se_nao_existir(
            conexao,
            "pontos_calibracao",
            "incerteza",
            "TEXT"
        )

        _adicionar_coluna_se_nao_existir(
            conexao,
            "pontos_calibracao",
            "criterio",
            "TEXT"
        )

        _adicionar_coluna_se_nao_existir(
            conexao,
            "pontos_calibracao",
            "valor_minimo",
            "REAL"
        )

        _adicionar_coluna_se_nao_existir(
            conexao,
            "pontos_calibracao",
            "valor_maximo",
            "REAL"
        )

        _adicionar_coluna_se_nao_existir(
            conexao,
            "pontos_calibracao",
            "classe_exigida",
            "TEXT"
        )

        _adicionar_coluna_se_nao_existir(
            conexao,
            "pontos_calibracao",
            "resultado",
            "TEXT"
        )

        _adicionar_coluna_se_nao_existir(
            conexao,
            "pontos_calibracao",
            "observacoes",
            "TEXT"
        )

        # ====================================================
        # ÍNDICES
        # ====================================================

        conexao.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_equipamentos_codigo
            ON equipamentos(codigo)
            """
        )

        conexao.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_equipamentos_tipo
            ON equipamentos(tipo_instrumento_id)
            """
        )

        conexao.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_equipamentos_plano
            ON equipamentos(plano_id)
            """
        )

        conexao.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_calibracoes_equipamento
            ON calibracoes(
                equipamento_id,
                data_calibracao
            )
            """
        )

        conexao.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_pontos_calibracao
            ON pontos_calibracao(
                calibracao_id,
                ordem
            )
            """
        )

        conexao.execute(
            """
            CREATE INDEX IF NOT EXISTS
            idx_pontos_plano
            ON pontos_plano(
                plano_id,
                ordem
            )
            """
        )

        conexao.commit()

        conexao.execute(
            "PRAGMA foreign_keys = ON"
        )

    except Exception:
        conexao.rollback()

        try:
            conexao.execute(
                "PRAGMA foreign_keys = ON"
            )
        except Exception:
            pass

        raise

    finally:
        conexao.close()