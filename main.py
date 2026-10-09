import sqlite3
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st

from app.database.db import conectar, criar_banco
from app.services.calibracao_service import (
    criar_calibracao,
    obter_calibracao,
    obter_pontos_calibracao,
    salvar_pontos_calibracao,
    atualizar_resultado_final_calibracao,
)


# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="Sistema de Gestão de Calibração",
    layout="wide",
    initial_sidebar_state="expanded",
)


# ============================================================
# IDENTIDADE VISUAL
# ============================================================

st.markdown(
    """
    <style>

    /* ========================================================
       CONFIGURAÇÃO GERAL
       ======================================================== */

    .stApp {
        background-color: #2b3035;
        color: #ffffff;
    }

    .main .block-container {
        max-width: 1500px;
        padding-top: 1.5rem;
        padding-bottom: 3rem;
    }

    /* ========================================================
       TEXTOS GERAIS
       ======================================================== */

    p,
    label,
    span,
    div,
    .stMarkdown,
    .stCaption {
        color: #ffffff;
    }

    h1,
    h2,
    h3,
    h4,
    h5,
    h6 {
        color: #ffffff !important;
    }

    /* Campos, seletores e menus escuros com texto claro */
    div[data-baseweb="select"] > div,
    div[data-baseweb="input"],
    div[data-baseweb="textarea"],
    input,
    textarea,
    [data-baseweb="popover"] ul,
    [data-baseweb="menu"],
    [role="listbox"],
    [role="option"] {
        background-color: #000000 !important;
        color: #ffffff !important;
        border-color: #454b51 !important;
    }
    div[data-baseweb="select"] span,
    div[data-baseweb="select"] input,
    [role="option"] * {
        color: #ffffff !important;
    }
    [data-testid="stDataFrame"] {
        color: #ffffff !important;
    }

    /* ========================================================
       CABEÇALHO
       ======================================================== */

    .calib-header {
        background: #000000;
        border-bottom: 4px solid #22282e;
        padding: 18px 28px;
        margin: -10px -10px 28px -10px;
        display: flex;
        align-items: center;
        gap: 22px;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.35);
        border-radius: 0 0 6px 6px;
    }

    .calib-header-title {
        font-size: 28px;
        font-weight: 700;
        color: #ffffff !important;
        margin: 0;
        line-height: 1.2;
    }

    .calib-header-subtitle {
        font-size: 14px;
        color: #c5cbd0 !important;
        margin-top: 6px;
        line-height: 1.4;
    }

    /* ========================================================
       CARDS DOS INDICADORES
       ======================================================== */

    [data-testid="stMetric"] {
        background: #000000;
        border: 1px solid #454b51;
        border-radius: 8px;
        padding: 18px;
        box-shadow: 0 2px 7px rgba(0, 0, 0, 0.30);
    }

    [data-testid="stMetricLabel"] {
        color: #c5cbd0 !important;
        font-size: 14px;
    }

    [data-testid="stMetricValue"] {
        color: #ffffff !important;
        font-weight: 700;
    }

    [data-testid="stMetricDelta"] {
        color: #ffffff !important;
    }

    /* ========================================================
       BOTÕES
       ======================================================== */

    .stButton > button {
        border-radius: 5px;
        border: 1px solid #555b61;
        background-color: #000000;
        color: #ffffff !important;
        font-weight: 600;
        min-height: 40px;
        transition: all 0.15s ease;
    }

    .stButton > button:hover {
        background-color: #171717;
        border-color: #777777;
        color: #ffffff !important;
    }

    button[kind="primary"] {
        background-color: #000000 !important;
        border-color: #555b61 !important;
        color: #ffffff !important;
    }

    button[kind="primary"]:hover {
        background-color: #171717 !important;
        border-color: #777777 !important;
        color: #ffffff !important;
    }

    /* ========================================================
       ABAS
       ======================================================== */

    .stTabs [data-baseweb="tab-list"] {
        gap: 4px;
        border-bottom: 1px solid #555b61;
    }

    .stTabs [data-baseweb="tab"] {
        padding: 12px 22px;
        font-weight: 600;
        color: #c5cbd0 !important;
    }

    .stTabs [aria-selected="true"] {
        color: #ffffff !important;
    }

    /* ========================================================
       EXPANDERS
       ======================================================== */

    [data-testid="stExpander"] {
        background-color: #000000 !important;
        border: 1px solid #454b51;
        border-radius: 7px;
        box-shadow: 0 1px 4px rgba(0, 0, 0, 0.30);
    }

    [data-testid="stExpander"] summary {
        background-color: #000000 !important;
        color: #ffffff !important;
    }

    [data-testid="stExpander"] summary span {
        color: #ffffff !important;
    }

    [data-testid="stExpander"] > div {
        background-color: #000000 !important;
        color: #ffffff !important;
    }

    /* ========================================================
       CAMPOS DE TEXTO
       ======================================================== */

    .stTextInput input,
    .stNumberInput input,
    .stDateInput input,
    .stTextArea textarea {
        background-color: #000000 !important;
        color: #ffffff !important;
        border: 1px solid #555b61 !important;
        border-radius: 5px;
        caret-color: #ffffff;
    }

    .stTextInput input::placeholder,
    .stNumberInput input::placeholder,
    .stDateInput input::placeholder,
    .stTextArea textarea::placeholder {
        color: #9da4aa !important;
    }

    .stTextInput input:focus,
    .stNumberInput input:focus,
    .stDateInput input:focus,
    .stTextArea textarea:focus {
        background-color: #000000 !important;
        color: #ffffff !important;
        border-color: #888f95 !important;
        box-shadow: none !important;
    }

    /* ========================================================
       SELECTBOX
       ======================================================== */

    div[data-baseweb="select"] > div {
        background-color: #000000 !important;
        color: #ffffff !important;
        border: 1px solid #555b61 !important;
        border-radius: 5px;
    }

    div[data-baseweb="select"] * {
        color: #ffffff !important;
    }

    div[data-baseweb="select"] svg {
        fill: #ffffff !important;
    }

    /* ========================================================
       MENUS / JANELAS DOS SELECTBOXS
       ======================================================== */

    [data-baseweb="popover"] {
        background-color: #000000 !important;
        color: #ffffff !important;
        border: 1px solid #555b61 !important;
    }

    [data-baseweb="popover"] * {
        color: #ffffff !important;
    }

    [role="listbox"] {
        background-color: #000000 !important;
        color: #ffffff !important;
    }

    [role="option"] {
        background-color: #000000 !important;
        color: #ffffff !important;
    }

    [role="option"]:hover {
        background-color: #222222 !important;
        color: #ffffff !important;
    }

    [aria-selected="true"][role="option"] {
        background-color: #222222 !important;
        color: #ffffff !important;
    }

    /* ========================================================
       CALENDÁRIO
       ======================================================== */

    [data-baseweb="calendar"] {
        background-color: #000000 !important;
        color: #ffffff !important;
    }

    [data-baseweb="calendar"] * {
        color: #ffffff !important;
    }

    [data-baseweb="calendar"] button {
        background-color: #000000 !important;
        color: #ffffff !important;
    }

    [data-baseweb="calendar"] button:hover {
        background-color: #222222 !important;
    }

    /* ========================================================
       TABELAS
       ======================================================== */

    [data-testid="stDataFrame"] {
        border: 1px solid #454b51;
        border-radius: 7px;
        overflow: hidden;
        background-color: #000000;
    }

    /* ========================================================
       ALERTAS
       ======================================================== */

    [data-testid="stAlert"] {
        border-radius: 6px;
    }

    /* ========================================================
       DIVISORES
       ======================================================== */

    hr {
        border-color: #555b61;
    }

    /* ========================================================
       SIDEBAR
       ======================================================== */

    section[data-testid="stSidebar"] {
        background-color: #000000;
    }

    section[data-testid="stSidebar"] * {
        color: #ffffff !important;
    }

    /* ========================================================
       CHECKBOX
       ======================================================== */

    [data-testid="stCheckbox"] label {
        color: #ffffff !important;
    }

    /* ========================================================
       RADIO / OUTROS CONTROLES
       ======================================================== */

    [data-testid="stRadio"] label {
        color: #ffffff !important;
    }

    [data-testid="stSelectbox"] label,
    [data-testid="stNumberInput"] label,
    [data-testid="stTextInput"] label,
    [data-testid="stTextArea"] label,
    [data-testid="stDateInput"] label {
        color: #ffffff !important;
    }

    </style>
    """,
    unsafe_allow_html=True,
)


# ============================================================
# INICIALIZAÇÃO DO BANCO
# ============================================================

if "banco_inicializado" not in st.session_state:
    criar_banco()
    st.session_state["banco_inicializado"] = True


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def executar_consulta(sql, parametros=()):
    conexao = conectar()

    try:
        return conexao.execute(sql, parametros).fetchall()

    finally:
        conexao.close()


def executar_consulta_unica(sql, parametros=()):
    conexao = conectar()

    try:
        return conexao.execute(sql, parametros).fetchone()

    finally:
        conexao.close()


def executar_comando(sql, parametros=()):
    conexao = conectar()

    try:
        cursor = conexao.execute(sql, parametros)
        conexao.commit()
        return cursor.lastrowid

    except Exception:
        conexao.rollback()
        raise

    finally:
        conexao.close()


# ============================================================
# CONSULTAS
# ============================================================

def buscar_equipamentos():
    return executar_consulta(
        """
        SELECT
            e.*,
            ti.nome AS tipo_instrumento,
            p.nome AS plano_nome,
            p.faixa AS plano_faixa,
            p.resolucao AS plano_resolucao,
            p.periodicidade_meses AS plano_periodicidade
        FROM equipamentos e
        LEFT JOIN tipos_instrumento ti
            ON ti.id = e.tipo_instrumento_id
        LEFT JOIN planos_calibracao p
            ON p.id = e.plano_id
        WHERE e.ativo = 1
        ORDER BY e.codigo
        """
    )


def buscar_tipos_instrumento():
    return executar_consulta(
        """
        SELECT
            id,
            nome,
            descricao
        FROM tipos_instrumento
        WHERE ativo = 1
        ORDER BY nome
        """
    )


def buscar_planos():
    return executar_consulta(
        """
        SELECT
            p.*,
            ti.nome AS tipo_instrumento
        FROM planos_calibracao p
        LEFT JOIN tipos_instrumento ti
            ON ti.id = p.tipo_instrumento_id
        WHERE p.ativo = 1
        ORDER BY ti.nome, p.nome
        """
    )


def buscar_calibracoes_equipamento(equipamento_id):
    return executar_consulta(
        """
        SELECT
            c.*,
            e.codigo AS equipamento_codigo,
            e.descricao AS equipamento_descricao
        FROM calibracoes c
        INNER JOIN equipamentos e
            ON e.id = c.equipamento_id
        WHERE c.equipamento_id = ?
        ORDER BY c.data_calibracao DESC, c.id DESC
        """,
        (equipamento_id,),
    )


def buscar_todas_calibracoes():
    return executar_consulta(
        """
        SELECT
            c.id,
            c.equipamento_id,
            c.data_calibracao,
            c.data_proxima_calibracao,
            c.laboratorio,
            c.certificado,
            c.resultado,
            c.resultado_final,
            c.responsavel,
            c.observacoes,
            e.codigo AS equipamento_codigo,
            e.descricao AS equipamento_descricao,
            ti.nome AS tipo_instrumento
        FROM calibracoes c
        INNER JOIN equipamentos e
            ON e.id = c.equipamento_id
        LEFT JOIN tipos_instrumento ti
            ON ti.id = e.tipo_instrumento_id
        ORDER BY
            c.data_proxima_calibracao,
            e.codigo
        """
    )


def buscar_pontos_plano(plano_id):
    return executar_consulta(
        """
        SELECT *
        FROM pontos_plano
        WHERE plano_id = ?
          AND ativo = 1
        ORDER BY ordem
        """,
        (plano_id,),
    )


# ============================================================
# FORMATAÇÃO
# ============================================================

def formatar_data(valor):
    if not valor:
        return "-"

    try:
        return datetime.strptime(
            str(valor)[:10],
            "%Y-%m-%d",
        ).strftime("%d/%m/%Y")

    except Exception:
        return str(valor)


def converter_data(valor):
    if isinstance(valor, date):
        return valor

    if not valor:
        return None

    try:
        return datetime.strptime(
            str(valor)[:10],
            "%Y-%m-%d",
        ).date()

    except Exception:
        return None


def formatar_valor(valor):
    if valor is None:
        return "-"

    try:
        numero = float(valor)

        if numero.is_integer():
            return str(int(numero))

        return f"{numero:.6f}".rstrip("0").rstrip(".")

    except Exception:
        return str(valor)


# ============================================================
# RESULTADO DOS PONTOS
# ============================================================

def calcular_resultado_ponto(ponto, valor):
    if valor is None or valor == "":
        return "Não informado"

    try:
        valor_numerico = float(valor)

    except Exception:
        return "Não informado"

    valor_minimo = ponto["valor_minimo"]
    valor_maximo = ponto["valor_maximo"]

    tolerancia_inferior = ponto["tolerancia_inferior"]
    tolerancia_superior = ponto["tolerancia_superior"]

    if valor_minimo is not None:
        if valor_numerico < float(valor_minimo):
            return "Reprovado"

    if valor_maximo is not None:
        if valor_numerico > float(valor_maximo):
            return "Reprovado"

    nominal = ponto["valor_nominal"]

    if nominal is not None:
        nominal = float(nominal)

        if tolerancia_inferior is not None:
            limite_inferior = (
                nominal + float(tolerancia_inferior)
            )

            if valor_numerico < limite_inferior:
                return "Reprovado"

        if tolerancia_superior is not None:
            limite_superior = (
                nominal + float(tolerancia_superior)
            )

            if valor_numerico > limite_superior:
                return "Reprovado"

    return "Aprovado"


def texto_resultado(resultado):
    if resultado == "Aprovado":
        return "Aprovado"

    if resultado == "Reprovado":
        return "Reprovado"

    if resultado == "Aprovado com restrição":
        return "Aprovado com restrição"

    return "Não informado"


# ============================================================
# CABEÇALHO
# ============================================================

col_logo, col_titulo = st.columns(
    [1, 7],
    vertical_alignment="center",
)

with col_logo:
    try:
        st.image(
            "assets/logo_mg.png",
            width=150,
        )
    except Exception:
        st.empty()

with col_titulo:
    st.markdown(
        """
        <div class="calib-header-title">
            Sistema de Gestão de Calibração
        </div>
        <div class="calib-header-subtitle">
            Controle de equipamentos, planos, calibrações,
            pontos de medição e cronograma.
        </div>
        """,
        unsafe_allow_html=True,
    )


# ============================================================
# CARREGAMENTO
# ============================================================

equipamentos = buscar_equipamentos()
tipos_instrumento = buscar_tipos_instrumento()
planos = buscar_planos()

hoje = date.today()

calibracoes_todas = buscar_todas_calibracoes()


# ============================================================
# INDICADORES
# ============================================================

vencidas = []

proximos_30 = []

limite_30 = hoje + timedelta(days=30)


for calibracao in calibracoes_todas:

    data_proxima = converter_data(
        calibracao["data_proxima_calibracao"]
    )

    if data_proxima:

        if data_proxima < hoje:
            vencidas.append(calibracao)

        elif hoje <= data_proxima <= limite_30:
            proximos_30.append(calibracao)


col1, col2, col3, col4 = st.columns(4)


with col1:
    st.metric(
        "Equipamentos",
        len(equipamentos),
    )


with col2:
    st.metric(
        "Calibrações",
        len(calibracoes_todas),
    )


with col3:
    st.metric(
        "Vencidas",
        len(vencidas),
    )


with col4:
    st.metric(
        "Próximas 30 dias",
        len(proximos_30),
    )


st.divider()


# ============================================================
# ABAS PRINCIPAIS
# ============================================================

aba_equipamentos, aba_cronograma = st.tabs(
    [
        "Equipamentos",
        "Cronograma",
    ]
)


# ============================================================
# ABA EQUIPAMENTOS
# ============================================================

with aba_equipamentos:

    with st.expander(
        "Cadastrar novo equipamento"
    ):

        if not planos:

            st.warning(
                "Não existem planos de calibração cadastrados."
            )

        else:

            opcoes_planos = {}

            for plano in planos:

                tipo = (
                    plano["tipo_instrumento"]
                    or "Sem tipo"
                )

                label = (
                    f"{tipo} — {plano['nome']}"
                )

                opcoes_planos[label] = plano


            labels_planos = list(
                opcoes_planos.keys()
            )


            with st.form(
                "form_novo_equipamento"
            ):

                col1, col2 = st.columns(2)


                with col1:

                    codigo = st.text_input(
                        "Código do equipamento *"
                    )

                    descricao = st.text_input(
                        "Descrição *"
                    )

                    fabricante = st.text_input(
                        "Fabricante"
                    )

                    modelo = st.text_input(
                        "Modelo"
                    )

                    numero_serie = st.text_input(
                        "Número de série"
                    )


                with col2:

                    plano_label = st.selectbox(
                        "Plano de calibração *",
                        labels_planos,
                    )

                    plano_selecionado = (
                        opcoes_planos[
                            plano_label
                        ]
                    )

                    faixa = st.text_input(
                        "Faixa"
                    )

                    resolucao = st.text_input(
                        "Resolução"
                    )

                    localizacao = st.text_input(
                        "Localização"
                    )

                    responsavel = st.text_input(
                        "Responsável"
                    )


                col3, col4 = st.columns(2)


                with col3:

                    periodicidade = st.number_input(
                        "Periodicidade (meses)",
                        min_value=1,
                        value=int(
                            plano_selecionado[
                                "periodicidade_meses"
                            ] or 12
                        ),
                        step=1,
                    )


                with col4:

                    observacoes = st.text_area(
                        "Observações"
                    )


                cadastrar = st.form_submit_button(
                    "Cadastrar equipamento",
                    type="primary",
                    use_container_width=True,
                )


                if cadastrar:

                    if not codigo.strip():

                        st.error(
                            "Informe o código do equipamento."
                        )

                    elif not descricao.strip():

                        st.error(
                            "Informe a descrição do equipamento."
                        )

                    else:

                        try:

                            executar_comando(
                                """
                                INSERT INTO equipamentos (
                                    codigo,
                                    descricao,
                                    tipo_instrumento_id,
                                    plano_id,
                                    fabricante,
                                    modelo,
                                    numero_serie,
                                    faixa,
                                    resolucao,
                                    localizacao,
                                    responsavel,
                                    periodicidade_meses,
                                    status,
                                    observacoes
                                )
                                VALUES (
                                    ?, ?, ?, ?, ?, ?, ?, ?, ?,
                                    ?, ?, ?, 'ATIVO', ?
                                )
                                """,
                                (
                                    codigo.strip(),
                                    descricao.strip(),
                                    plano_selecionado[
                                        "tipo_instrumento_id"
                                    ],
                                    plano_selecionado["id"],
                                    fabricante.strip(),
                                    modelo.strip(),
                                    numero_serie.strip(),
                                    faixa.strip(),
                                    resolucao.strip(),
                                    localizacao.strip(),
                                    responsavel.strip(),
                                    periodicidade,
                                    observacoes.strip(),
                                ),
                            )

                            st.success(
                                "Equipamento cadastrado com sucesso."
                            )

                            st.rerun()

                        except sqlite3.IntegrityError:

                            st.error(
                                "Já existe um equipamento "
                                "com esse código."
                            )

                        except Exception as erro:

                            st.error(
                                f"Erro ao cadastrar equipamento: {erro}"
                            )


    st.subheader("Equipamentos")


    if not equipamentos:

        st.info(
            "Nenhum equipamento cadastrado."
        )

    else:

        busca = st.text_input(
            "Pesquisar equipamento",
            placeholder=(
                "Digite código, descrição, fabricante "
                "ou número de série..."
            ),
        )


        busca_lower = busca.strip().lower()

        equipamentos_filtrados = []


        for equipamento in equipamentos:

            texto_busca = " ".join(
                [
                    str(
                        equipamento["codigo"]
                        or ""
                    ),
                    str(
                        equipamento["descricao"]
                        or ""
                    ),
                    str(
                        equipamento["fabricante"]
                        or ""
                    ),
                    str(
                        equipamento["modelo"]
                        or ""
                    ),
                    str(
                        equipamento["numero_serie"]
                        or ""
                    ),
                ]
            ).lower()


            if (
                not busca_lower
                or busca_lower in texto_busca
            ):

                equipamentos_filtrados.append(
                    equipamento
                )


        st.caption(
            f"{len(equipamentos_filtrados)} "
            "equipamento(s) encontrado(s)."
        )


        if not equipamentos_filtrados:

            st.warning(
                "Nenhum equipamento encontrado."
            )

        else:

            opcoes_equipamentos = {}


            for equipamento in equipamentos_filtrados:

                label = (
                    f"{equipamento['codigo']} — "
                    f"{equipamento['descricao']}"
                )

                opcoes_equipamentos[
                    label
                ] = equipamento["id"]


            equipamento_label = st.selectbox(
                "Selecione o equipamento",
                list(
                    opcoes_equipamentos.keys()
                ),
            )


            equipamento_id = (
                opcoes_equipamentos[
                    equipamento_label
                ]
            )


            equipamento = next(
                e
                for e in equipamentos
                if e["id"] == equipamento_id
            )


            st.divider()

            st.subheader(
                f"{equipamento['codigo']} — "
                f"{equipamento['descricao']}"
            )


            aba_dados, aba_edicao, aba_calibracoes = st.tabs(
                [
                    "Dados",
                    "Editar",
                    "Calibrações",
                ]
            )


            with aba_dados:

                col1, col2, col3 = st.columns(3)


                with col1:

                    st.write(
                        "**Código:**",
                        equipamento["codigo"],
                    )

                    st.write(
                        "**Tipo:**",
                        equipamento[
                            "tipo_instrumento"
                        ] or "-",
                    )

                    st.write(
                        "**Fabricante:**",
                        equipamento[
                            "fabricante"
                        ] or "-",
                    )

                    st.write(
                        "**Modelo:**",
                        equipamento[
                            "modelo"
                        ] or "-",
                    )


                with col2:

                    st.write(
                        "**Número de série:**",
                        equipamento[
                            "numero_serie"
                        ] or "-",
                    )

                    st.write(
                        "**Faixa:**",
                        equipamento[
                            "faixa"
                        ] or "-",
                    )

                    st.write(
                        "**Resolução:**",
                        equipamento[
                            "resolucao"
                        ] or "-",
                    )

                    st.write(
                        "**Localização:**",
                        equipamento[
                            "localizacao"
                        ] or "-",
                    )


                with col3:

                    st.write(
                        "**Plano:**",
                        equipamento[
                            "plano_nome"
                        ] or "-",
                    )

                    st.write(
                        "**Periodicidade:**",
                        (
                            f"{equipamento['periodicidade_meses']} meses"
                            if equipamento[
                                "periodicidade_meses"
                            ]
                            else "-"
                        ),
                    )

                    st.write(
                        "**Última calibração:**",
                        formatar_data(
                            equipamento[
                                "data_ultima_calibracao"
                            ]
                        ),
                    )

                    st.write(
                        "**Próxima calibração:**",
                        formatar_data(
                            equipamento[
                                "data_proxima_calibracao"
                            ]
                        ),
                    )


                if equipamento["observacoes"]:

                    st.divider()

                    st.write(
                        "**Observações:**"
                    )

                    st.write(
                        equipamento["observacoes"]
                    )


            with aba_edicao:

                opcoes_planos = {}


                for plano in planos:

                    tipo = (
                        plano["tipo_instrumento"]
                        or "Sem tipo"
                    )

                    label = (
                        f"{tipo} — {plano['nome']}"
                    )

                    opcoes_planos[label] = plano


                plano_atual_label = None


                for label, plano in opcoes_planos.items():

                    if (
                        plano["id"]
                        == equipamento["plano_id"]
                    ):

                        plano_atual_label = label

                        break


                if plano_atual_label is None:

                    plano_atual_label = (
                        list(
                            opcoes_planos.keys()
                        )[0]
                    )


                with st.form(
                    f"form_edicao_{equipamento_id}"
                ):

                    col1, col2 = st.columns(2)


                    with col1:

                        descricao_edit = st.text_input(
                            "Descrição",
                            value=(
                                equipamento[
                                    "descricao"
                                ] or ""
                            ),
                        )

                        fabricante_edit = st.text_input(
                            "Fabricante",
                            value=(
                                equipamento[
                                    "fabricante"
                                ] or ""
                            ),
                        )

                        modelo_edit = st.text_input(
                            "Modelo",
                            value=(
                                equipamento[
                                    "modelo"
                                ] or ""
                            ),
                        )

                        serie_edit = st.text_input(
                            "Número de série",
                            value=(
                                equipamento[
                                    "numero_serie"
                                ] or ""
                            ),
                        )

                        faixa_edit = st.text_input(
                            "Faixa",
                            value=(
                                equipamento[
                                    "faixa"
                                ] or ""
                            ),
                        )


                    with col2:

                        lista_planos = list(
                            opcoes_planos.keys()
                        )


                        plano_edit_label = st.selectbox(
                            "Plano de calibração",
                            lista_planos,
                            index=lista_planos.index(
                                plano_atual_label
                            ),
                        )


                        resolucao_edit = st.text_input(
                            "Resolução",
                            value=(
                                equipamento[
                                    "resolucao"
                                ] or ""
                            ),
                        )

                        localizacao_edit = st.text_input(
                            "Localização",
                            value=(
                                equipamento[
                                    "localizacao"
                                ] or ""
                            ),
                        )

                        responsavel_edit = st.text_input(
                            "Responsável",
                            value=(
                                equipamento[
                                    "responsavel"
                                ] or ""
                            ),
                        )

                        periodicidade_edit = st.number_input(
                            "Periodicidade (meses)",
                            min_value=1,
                            value=int(
                                equipamento[
                                    "periodicidade_meses"
                                ] or 12
                            ),
                            step=1,
                        )


                    observacoes_edit = st.text_area(
                        "Observações",
                        value=(
                            equipamento[
                                "observacoes"
                            ] or ""
                        ),
                    )


                    salvar_edicao = st.form_submit_button(
                        "Salvar alterações",
                        type="primary",
                        use_container_width=True,
                    )


                    if salvar_edicao:

                        plano_edit = (
                            opcoes_planos[
                                plano_edit_label
                            ]
                        )


                        try:

                            executar_comando(
                                """
                                UPDATE equipamentos
                                SET
                                    descricao = ?,
                                    tipo_instrumento_id = ?,
                                    plano_id = ?,
                                    fabricante = ?,
                                    modelo = ?,
                                    numero_serie = ?,
                                    faixa = ?,
                                    resolucao = ?,
                                    localizacao = ?,
                                    responsavel = ?,
                                    periodicidade_meses = ?,
                                    observacoes = ?,
                                    atualizado_em = CURRENT_TIMESTAMP
                                WHERE id = ?
                                """,
                                (
                                    descricao_edit.strip(),
                                    plano_edit[
                                        "tipo_instrumento_id"
                                    ],
                                    plano_edit["id"],
                                    fabricante_edit.strip(),
                                    modelo_edit.strip(),
                                    serie_edit.strip(),
                                    faixa_edit.strip(),
                                    resolucao_edit.strip(),
                                    localizacao_edit.strip(),
                                    responsavel_edit.strip(),
                                    periodicidade_edit,
                                    observacoes_edit.strip(),
                                    equipamento_id,
                                ),
                            )


                            st.success(
                                "Equipamento atualizado."
                            )

                            st.rerun()


                        except Exception as erro:

                            st.error(
                                f"Erro ao atualizar: {erro}"
                            )


                st.divider()
                st.warning(
                    "A exclusão remove o equipamento e todo o histórico associado. "
                    "Essa ação é definitiva."
                )
                chave_confirmar = f"confirmar_exclusao_{equipamento_id}"
                if st.button("Excluir equipamento", key=f"excluir_{equipamento_id}"):
                    st.session_state[chave_confirmar] = True
                if st.session_state.get(chave_confirmar, False):
                    st.error("Confirme a exclusão definitiva deste equipamento.")
                    col_confirmar, col_cancelar = st.columns(2)
                    with col_confirmar:
                        if st.button("Sim, excluir definitivamente", key=f"confirmar_excluir_{equipamento_id}", type="primary"):
                            conexao = conectar()
                            try:
                                conexao.execute("BEGIN")
                                ids = conexao.execute(
                                    "SELECT id FROM calibracoes WHERE equipamento_id = ?",
                                    (equipamento_id,),
                                ).fetchall()
                                for registro in ids:
                                    conexao.execute(
                                        "DELETE FROM pontos_calibracao WHERE calibracao_id = ?",
                                        (registro["id"],),
                                    )
                                conexao.execute("DELETE FROM calibracoes WHERE equipamento_id = ?", (equipamento_id,))
                                conexao.execute("DELETE FROM equipamentos WHERE id = ?", (equipamento_id,))
                                conexao.commit()
                                st.session_state.pop(chave_confirmar, None)
                                st.success("Equipamento e histórico excluídos.")
                                st.rerun()
                            except Exception as erro:
                                conexao.rollback()
                                st.error(f"Não foi possível excluir o equipamento: {erro}")
                            finally:
                                conexao.close()
                    with col_cancelar:
                        if st.button("Cancelar", key=f"cancelar_excluir_{equipamento_id}"):
                            st.session_state.pop(chave_confirmar, None)
                            st.rerun()


            with aba_calibracoes:

                st.subheader(
                    "Nova calibração"
                )


                with st.form(
                    f"form_nova_calibracao_{equipamento_id}"
                ):

                    col1, col2 = st.columns(2)


                    with col1:
                        data_calibracao = st.date_input(
                            "Data da calibração",
                            value=date.today(),
                        )
                        responsavel_calibracao = st.text_input(
                            "Responsável pela calibração *",
                            value=(equipamento["responsavel"] or ""),
                        )
                        laboratorio = st.text_input("Laboratório")
                        certificado = st.text_input("Certificado")

                    with col2:
                        opcoes_resultado_final = [
                            "APROVADO",
                            "REPROVADO - ORIENTAÇÃO INDICATIVA",
                            "REPROVADO - DESATIVADO",
                        ]
                        resultado_final_novo = st.selectbox(
                            "Resultado final *",
                            opcoes_resultado_final,
                        )
                        observacoes_calibracao = st.text_area("Observações")


                    criar = st.form_submit_button(
                        "Criar calibração",
                        type="primary",
                        use_container_width=True,
                    )


                    if criar:

                        try:

                            calibracao_id = criar_calibracao(
                                equipamento_id=equipamento_id,
                                data_calibracao=data_calibracao,
                                responsavel=(responsavel_calibracao.strip() or None),
                                resultado_final=resultado_final_novo,
                                laboratorio=(
                                    laboratorio.strip()
                                    or None
                                ),
                                certificado=(
                                    certificado.strip()
                                    or None
                                ),
                                observacoes=(
                                    observacoes_calibracao.strip()
                                    or None
                                ),
                            )


                            st.session_state[
                                f"calibracao_selecionada_"
                                f"{equipamento_id}"
                            ] = calibracao_id


                            st.success(
                                f"Calibração #{calibracao_id} criada."
                            )


                            st.rerun()


                        except Exception as erro:

                            st.error(
                                f"Erro ao criar calibração: {erro}"
                            )


                st.divider()


                historico = (
                    buscar_calibracoes_equipamento(
                        equipamento_id
                    )
                )


                st.subheader(
                    f"Histórico de calibrações "
                    f"({len(historico)})"
                )


                if not historico:

                    st.info(
                        "Este equipamento ainda não possui "
                        "calibrações registradas."
                    )

                else:

                    ids_calibracoes = [
                        c["id"]
                        for c in historico
                    ]


                    chave_selecao = (
                        f"calibracao_selecionada_"
                        f"{equipamento_id}"
                    )


                    selecionada_atual = (
                        st.session_state.get(
                            chave_selecao
                        )
                    )


                    if (
                        selecionada_atual
                        not in ids_calibracoes
                    ):

                        selecionada_atual = (
                            ids_calibracoes[0]
                        )


                    def formatar_calibracao(
                        calibracao_id
                    ):

                        calibracao = next(
                            c
                            for c in historico
                            if c["id"]
                            == calibracao_id
                        )


                        resultado = (
                            calibracao["resultado_final"]
                            or "Resultado não definido"
                        )


                        return (
                            f"#{calibracao['id']} — "
                            f"{formatar_data(calibracao['data_calibracao'])}"
                            f" — {resultado}"
                        )


                    calibracao_selecionada = (
                        st.selectbox(
                            "Selecione a calibração",
                            ids_calibracoes,
                            index=ids_calibracoes.index(
                                selecionada_atual
                            ),
                            format_func=(
                                formatar_calibracao
                            ),
                        )
                    )


                    st.session_state[
                        chave_selecao
                    ] = calibracao_selecionada


                    calibracao = obter_calibracao(
                        calibracao_selecionada
                    )


                    pontos = obter_pontos_calibracao(
                        calibracao_selecionada
                    )


                    if calibracao:

                        col1, col2, col3, col4 = (
                            st.columns(4)
                        )


                        with col1:

                            st.write(
                                "**Data:**",
                                formatar_data(
                                    calibracao[
                                        "data_calibracao"
                                    ]
                                ),
                            )


                        with col2:

                            st.write(
                                "**Próxima:**",
                                formatar_data(
                                    calibracao[
                                        "data_proxima_calibracao"
                                    ]
                                ),
                            )


                        with col3:

                            st.write(
                                "**Laboratório:**",
                                calibracao[
                                    "laboratorio"
                                ] or "-",
                            )


                        with col4:
                            st.write(
                                "**Resultado final:**",
                                calibracao["resultado_final"] or "Resultado não definido",
                            )

                        st.write(
                            "**Responsável pela calibração:**",
                            calibracao["responsavel"] or "Não informado",
                        )


                        if calibracao[
                            "certificado"
                        ]:

                            st.write(
                                "**Certificado:**",
                                calibracao[
                                    "certificado"
                                ],
                            )


                        if calibracao[
                            "observacoes"
                        ]:

                            st.write(
                                "**Observações:**",
                                calibracao[
                                    "observacoes"
                                ],
                            )


                    st.divider()


                    st.subheader("Resultado final da calibração")
                    opcoes_resultado_final = [
                        "APROVADO",
                        "REPROVADO - ORIENTAÇÃO INDICATIVA",
                        "REPROVADO - DESATIVADO",
                    ]
                    resultado_salvo = calibracao["resultado_final"] or opcoes_resultado_final[0]
                    if resultado_salvo not in opcoes_resultado_final:
                        resultado_salvo = opcoes_resultado_final[0]
                    with st.form(f"form_resultado_final_{calibracao_selecionada}"):
                        resultado_final_editado = st.selectbox(
                            "Parecer final",
                            opcoes_resultado_final,
                            index=opcoes_resultado_final.index(resultado_salvo),
                        )
                        salvar_resultado_final = st.form_submit_button(
                            "Salvar resultado final",
                            type="primary",
                        )
                    if salvar_resultado_final:
                        try:
                            atualizar_resultado_final_calibracao(
                                calibracao_selecionada,
                                resultado_final_editado,
                            )
                            st.success("Resultado final salvo.")
                            st.rerun()
                        except Exception as erro:
                            st.error(f"Erro ao salvar resultado final: {erro}")

                    st.divider()
                    st.subheader(f"Referência de calibração — pontos nominais ({len(pontos)})")
                    st.caption(
                        "Consulte estes critérios durante a verificação física do instrumento. "
                        "O sistema não solicita valores encontrados nem calcula erros ou aprovações por ponto."
                    )
                    if not pontos:
                        st.warning("Este plano não possui pontos de referência cadastrados.")
                    else:
                        linhas_referencia = []
                        for indice, ponto in enumerate(pontos, start=1):
                            tipo_ponto = (ponto["tipo_ponto"] or "NUMERICO").replace("_", " ").title()
                            nominal = formatar_valor(ponto["valor_nominal"])
                            minimo = formatar_valor(ponto["valor_minimo"])
                            maximo = formatar_valor(ponto["valor_maximo"])
                            tol_inf = formatar_valor(ponto["tolerancia_inferior"])
                            tol_sup = formatar_valor(ponto["tolerancia_superior"])
                            criterios = ponto["criterio"] or ""
                            if ponto["classe_exigida"]:
                                criterios = (criterios + " | " if criterios else "") + f"Classe exigida: {ponto['classe_exigida']}"
                            if minimo != "-" or maximo != "-":
                                criterios = (criterios + " | " if criterios else "") + f"Faixa permitida: {minimo} a {maximo}"
                            linhas_referencia.append({
                                "Ponto": ponto["ordem_original"] or indice,
                                "Tipo": tipo_ponto,
                                "Verificação / descrição": ponto["descricao"] or "-",
                                "Nominal": f"{nominal} {ponto['unidade'] or ''}".strip() if nominal != "-" else "-",
                                "Tolerância inferior": tol_inf,
                                "Tolerância superior": tol_sup,
                                "Incerteza": ponto["incerteza"] or "-",
                                "Critério / observações": criterios or "-",
                            })
                        st.dataframe(
                            pd.DataFrame(linhas_referencia),
                            use_container_width=True,
                            hide_index=True,
                        )


# ============================================================
# ABA CRONOGRAMA
# ============================================================

with aba_cronograma:
    st.subheader("Cronograma de Calibração")

    todos_equipamentos = buscar_equipamentos()
    historico_global = executar_consulta(
        """
        SELECT c.id, c.equipamento_id, c.data_calibracao,
               c.data_proxima_calibracao, c.resultado_final,
               c.responsavel, e.codigo, e.descricao
        FROM calibracoes c
        JOIN equipamentos e ON e.id = c.equipamento_id
        WHERE e.ativo = 1
        ORDER BY c.data_calibracao, c.id
        """
    )
    historico_por_equipamento = {}
    for reg in historico_global:
        historico_por_equipamento.setdefault(reg["equipamento_id"], []).append(reg)

    labels_equip = {
        f"{eq['codigo']} — {eq['descricao']}": eq
        for eq in todos_equipamentos
    }
    escolha_equip = st.selectbox(
        "Próxima calibração — consultar equipamento",
        list(labels_equip.keys()),
        key="cronograma_consulta_equipamento",
    ) if labels_equip else None
    if escolha_equip:
        eq = labels_equip[escolha_equip]
        hist_eq = historico_por_equipamento.get(eq["id"], [])
        if hist_eq:
            ultima = max(hist_eq, key=lambda x: (x["data_calibracao"] or "", x["id"]))
            st.info(f"Próxima calibração prevista: {formatar_data(ultima['data_proxima_calibracao'])}")
        else:
            st.info("Este equipamento ainda não possui calibração registrada; a próxima data será calculada após a primeira calibração.")

    st.divider()
    filtro_status_atual = st.selectbox(
        "Status do equipamento",
        ["Todos", "Vencidas", "Próximas (30 dias)", "Programadas", "Sem calibração"],
        key="cronograma_filtro_status_atual",
    )
    resumo_status = []
    limite_proximo = date.today() + timedelta(days=30)
    for eq in todos_equipamentos:
        hist_eq = historico_por_equipamento.get(eq["id"], [])
        ultima_eq = max(hist_eq, key=lambda x: (x["data_calibracao"] or "", x["id"])) if hist_eq else None
        prox_eq = converter_data(ultima_eq["data_proxima_calibracao"]) if ultima_eq else None
        if not ultima_eq:
            status_eq = "Sem calibração"
        elif prox_eq and prox_eq < hoje:
            status_eq = "Vencidas"
        elif prox_eq and prox_eq <= limite_proximo:
            status_eq = "Próximas (30 dias)"
        else:
            status_eq = "Programadas" if prox_eq else "Sem calibração"
        resumo_status.append({
            "Código": eq["codigo"],
            "Equipamento": eq["descricao"],
            "Próxima calibração": formatar_data(prox_eq.isoformat()) if prox_eq else "-",
            "Status": status_eq,
        })
    if filtro_status_atual != "Todos":
        st.dataframe(
            pd.DataFrame([r for r in resumo_status if r["Status"] == filtro_status_atual]),
            use_container_width=True,
            hide_index=True,
        )

    st.divider()
    hoje = date.today()
    meses = []
    for deslocamento in range(-12, 25):
        ano = hoje.year + (hoje.month - 1 + deslocamento) // 12
        mes = (hoje.month - 1 + deslocamento) % 12 + 1
        meses.append(f"{ano:04d}-{mes:02d}")
    mes_atual = f"{hoje.year:04d}-{hoje.month:02d}"
    mes_escolhido = st.selectbox(
        "Mês do cronograma",
        meses,
        index=meses.index(mes_atual),
        format_func=lambda x: datetime.strptime(x, "%Y-%m").strftime("%B/%Y").capitalize(),
    )
    inicio_mes = date.fromisoformat(mes_escolhido + "-01")
    if inicio_mes.month == 12:
        inicio_proximo = date(inicio_mes.year + 1, 1, 1)
    else:
        inicio_proximo = date(inicio_mes.year, inicio_mes.month + 1, 1)
    fim_mes = inicio_proximo - timedelta(days=1)

    eventos_mes_por_equipamento = {}
    vencidas_atuais = []
    for eq in todos_equipamentos:
        hist = sorted(
            historico_por_equipamento.get(eq["id"], []),
            key=lambda x: (x["data_calibracao"] or "", x["id"]),
        )
        if not hist:
            continue
        # Cada registro histórico contém a data prevista para a calibração seguinte.
        for i, reg in enumerate(hist):
            vencimento = converter_data(reg["data_proxima_calibracao"])
            if not vencimento:
                continue
            proxima_registrada = hist[i + 1] if i + 1 < len(hist) else None
            data_execucao = converter_data(proxima_registrada["data_calibracao"]) if proxima_registrada else None
            if inicio_mes <= vencimento <= fim_mes:
                feita = bool(data_execucao and data_execucao <= fim_mes and data_execucao >= inicio_mes)
                eventos_mes_por_equipamento[eq["id"]] = {
                    "Código": eq["codigo"],
                    "Equipamento": eq["descricao"],
                    "Data prevista": formatar_data(vencimento.isoformat()),
                    "Situação": "FEITO" if feita else "PENDENTE",
                    "Data realizada": formatar_data(data_execucao.isoformat()) if feita else "-",
                }
        # Vencida atual: vencimento mais recente já passou e ainda não existe calibração posterior.
        ultima = hist[-1]
        vencimento_atual = converter_data(ultima["data_proxima_calibracao"])
        if vencimento_atual and vencimento_atual < hoje:
            vencidas_atuais.append({
                "Código": eq["codigo"],
                "Equipamento": eq["descricao"],
                "Data em que deveria calibrar": formatar_data(vencimento_atual.isoformat()),
            })

    eventos_mes = list(eventos_mes_por_equipamento.values())
    df_mes = pd.DataFrame(eventos_mes, columns=["Código", "Equipamento", "Data prevista", "Situação", "Data realizada"])
    feitos = sum(1 for item in eventos_mes if item["Situação"] == "FEITO")
    pendentes = sum(1 for item in eventos_mes if item["Situação"] == "PENDENTE")
    total_mes = len(eventos_mes)
    c1, c2, c3 = st.columns(3)
    c1.metric("Calibrações do mês", total_mes)
    c2.metric("Feitos", feitos)
    c3.metric("Falta fazer", pendentes)

    st.subheader("Equipamentos previstos para o mês")
    if df_mes.empty:
        st.info("Não há calibrações previstas para este mês com base no histórico registrado.")
    else:
        def colorir_situacao(linha):
            cor = "background-color: #14532d; color: #ffffff" if linha["Situação"] == "FEITO" else "background-color: #7f1d1d; color: #ffffff"
            return [cor if coluna == "Situação" else "" for coluna in linha.index]

        st.dataframe(
            df_mes.style.apply(colorir_situacao, axis=1),
            use_container_width=True,
            hide_index=True,
            column_config={
                "Situação": st.column_config.TextColumn("Situação", help="FEITO ou PENDENTE conforme o histórico de calibração."),
            },
        )
        st.caption("Os vencimentos permanecem no mês original para manter o total previsto, mesmo quando a calibração é feita depois.")

    st.divider()
    st.subheader("Vencidas")
    df_vencidas = pd.DataFrame(vencidas_atuais, columns=["Código", "Equipamento", "Data em que deveria calibrar"])
    if df_vencidas.empty:
        st.success("Não há equipamentos vencidos no momento.")
    else:
        st.dataframe(df_vencidas, use_container_width=True, hide_index=True)
