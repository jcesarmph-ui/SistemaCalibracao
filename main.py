import sqlite3
from io import BytesIO
from datetime import date, datetime, timedelta

import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt

from app.database.db import conectar, criar_banco
from app.interface import botao_lixeira, pagina_lixeira, tabela_status, sucesso
from app.services.lixeira_service import contadores
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

if "banco_lixeira_inicializado" not in st.session_state:
    criar_banco()
    st.session_state["banco_lixeira_inicializado"] = True


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
            (SELECT c.data_calibracao FROM calibracoes c WHERE c.equipamento_id = e.id AND c.excluido_em IS NULL ORDER BY c.data_calibracao DESC, c.id DESC LIMIT 1) AS ultima_visivel,
            (SELECT c.data_proxima_calibracao FROM calibracoes c WHERE c.equipamento_id = e.id AND c.excluido_em IS NULL ORDER BY c.data_calibracao DESC, c.id DESC LIMIT 1) AS proxima_visivel,
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
        WHERE e.ativo = 1 AND e.excluido_em IS NULL
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
        WHERE p.ativo = 1 AND p.excluido_em IS NULL
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
        WHERE c.equipamento_id = ? AND c.excluido_em IS NULL AND e.excluido_em IS NULL
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
        WHERE c.excluido_em IS NULL AND e.excluido_em IS NULL AND e.ativo = 1
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
          AND ativo = 1 AND excluido_em IS NULL
          AND EXISTS (SELECT 1 FROM planos_calibracao WHERE id = pontos_plano.plano_id AND excluido_em IS NULL)
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

def _numero_incerteza(valor):
    """Converte incerteza textual (ex.: '0,2', '±0.2', '0.2 mm') em número."""
    if valor is None:
        return None
    texto = str(valor).strip().replace(",", ".")
    if not texto:
        return None
    import re
    encontrado = re.search(r"[-+]?\d+(?:\.\d+)?(?:[eE][-+]?\d+)?", texto)
    if not encontrado:
        raise ValueError(f"Incerteza inválida: {valor!r}")
    try:
        return abs(float(encontrado.group(0)))
    except (TypeError, ValueError):
        return 0.0



# FUNCAO DO DESVIO FINAL COM SINAL

def desvio_final_com_incerteza(encontrado, nominal, incerteza):
    if encontrado is None or nominal is None:
        return None

    desvio = float(encontrado) - float(nominal)
    u = _numero_incerteza(incerteza)
    if u is None:
        return None
    u = abs(u)

    if desvio < 0:
        return desvio - u

    return desvio + u



def calcular_resultado_ponto(ponto, valor):
    if valor is None or valor == "":
        return "Não informado"

    try:
        valor_numerico = float(valor)
    except (TypeError, ValueError):
        return "Não informado"

    valor_minimo = ponto["valor_minimo"]
    valor_maximo = ponto["valor_maximo"]
    tolerancia_inferior = ponto["tolerancia_inferior"]
    tolerancia_superior = ponto["tolerancia_superior"]
    incerteza = _numero_incerteza(ponto["incerteza"] if "incerteza" in ponto.keys() else None)

    if incerteza is None:
        return "Não avaliado: incerteza ausente"

    # Avalia a faixa completa considerando a incerteza: [valor - U, valor + U].
    # Assim, a incerteza é somada ao desvio em módulo para a verificação de aceitação.
    faixa_inferior = valor_numerico - incerteza
    faixa_superior = valor_numerico + incerteza

    if valor_minimo is not None and faixa_inferior < float(valor_minimo):
        return "Reprovado"
    if valor_maximo is not None and faixa_superior > float(valor_maximo):
        return "Reprovado"

    nominal = ponto["valor_nominal"]
    if nominal is not None:
        nominal = float(nominal)
        if tolerancia_inferior is not None:
            limite_inferior = nominal + float(tolerancia_inferior)
            if faixa_inferior < limite_inferior:
                return "Reprovado"
        if tolerancia_superior is not None:
            limite_superior = nominal + float(tolerancia_superior)
            if faixa_superior > limite_superior:
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

if "mensagem_operacao" in st.session_state:
    st.success(st.session_state.pop("mensagem_operacao"))

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


ultimas_calibracoes = {}
for registro in calibracoes_todas:
    atual = ultimas_calibracoes.get(registro["equipamento_id"])
    if atual is None or (registro["data_calibracao"], registro["id"]) > (atual["data_calibracao"], atual["id"]):
        ultimas_calibracoes[registro["equipamento_id"]] = registro

for calibracao in ultimas_calibracoes.values():

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


st.caption(f"Registros na lixeira: {sum(contadores().values())}")
st.divider()


# ============================================================
# ABAS PRINCIPAIS
# ============================================================

aba_equipamentos, aba_cronograma, aba_lixeira = st.tabs(
    [
        "Equipamentos",
        "Cronograma",
        "Lixeira",
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
                    custo_compra = st.number_input(
                        "Custo de compra (R$)", min_value=0.0,
                        value=0.0, step=50.0, format="%.2f"
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
                    width="stretch",
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
                                    observacoes,
                                    custo_compra
                                )
                                VALUES (
                                    ?, ?, ?, ?, ?, ?, ?, ?, ?,
                                    ?, ?, ?, 'ATIVO', ?, ?
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
                                    custo_compra,
                                ),
                            )

                            sucesso("Equipamento cadastrado com sucesso.")

                        except sqlite3.IntegrityError:

                            st.error(
                                "Já existe um equipamento "
                                "com esse código."
                            )

                        except Exception as erro:

                            st.error(
                                f"Erro ao cadastrar equipamento: {erro}"
                            )


    with st.expander("Gerenciar tipos, planos e pontos nominais", expanded=False):
        st.markdown("### Criar plano para um tipo de instrumento")
        tipo_existente_labels = {f"{t['nome']} (ID {t['id']})": t['id'] for t in tipos_instrumento}
        tipo_opcao = st.radio("Tipo de instrumento", ["Usar tipo existente", "Criar novo tipo"], horizontal=True, key="tipo_opcao_criar_plano")
        with st.form("form_criar_plano_novo"):
            tipo_id_existente = None
            novo_tipo_nome = ""
            novo_tipo_descricao = ""
            if tipo_opcao == "Usar tipo existente":
                if tipo_existente_labels:
                    tipo_label = st.selectbox("Tipo cadastrado", list(tipo_existente_labels))
                    tipo_id_existente = tipo_existente_labels[tipo_label]
                else:
                    st.info("Ainda não há tipos cadastrados; escolha criar um novo tipo.")
            else:
                novo_tipo_nome = st.text_input("Nome do novo tipo *")
                novo_tipo_descricao = st.text_input("Descrição do tipo")
            nome_plano = st.text_input("Nome do plano *")
            faixa_plano = st.text_input("Faixa do instrumento")
            resolucao_plano = st.text_input("Resolução")
            periodicidade_plano = st.number_input("Periodicidade (meses)", min_value=1, value=12, step=1)
            observacoes_plano = st.text_area("Observações do plano")
            criar_plano_btn = st.form_submit_button("Criar tipo/plano", type="primary")
        if criar_plano_btn:
            try:
                if not nome_plano.strip():
                    st.error("Informe o nome do plano.")
                elif tipo_opcao == "Usar tipo existente" and tipo_id_existente is None:
                    st.error("Cadastre um tipo antes de criar o plano.")
                else:
                    conn = conectar()
                    try:
                        conn.execute("BEGIN")
                        if tipo_opcao == "Criar novo tipo":
                            if not novo_tipo_nome.strip():
                                raise ValueError("Informe o nome do novo tipo.")
                            cur = conn.execute("INSERT INTO tipos_instrumento (nome, descricao, ativo) VALUES (?, ?, 1)", (novo_tipo_nome.strip(), novo_tipo_descricao.strip() or None))
                            tipo_id = cur.lastrowid
                        else:
                            tipo_id = tipo_id_existente
                        conn.execute("INSERT INTO planos_calibracao (tipo_instrumento_id, nome, faixa, resolucao, periodicidade_meses, observacoes, ativo) VALUES (?, ?, ?, ?, ?, ?, 1)", (tipo_id, nome_plano.strip(), faixa_plano.strip() or None, resolucao_plano.strip() or None, int(periodicidade_plano), observacoes_plano.strip() or None))
                        conn.commit()
                    except Exception:
                        conn.rollback()
                        raise
                    finally:
                        conn.close()
                    sucesso("Tipo/plano criado. Agora adicione os pontos nominais abaixo.")
            except Exception as erro:
                st.error(f"Não foi possível criar o tipo/plano: {erro}")

        st.divider()
        st.markdown("### Adicionar ou editar pontos nominais")
        planos_ativos = buscar_planos()
        if planos_ativos:
            mapa_planos = {f"{pl['tipo_instrumento'] or 'Sem tipo'} — {pl['nome']} (ID {pl['id']})": pl['id'] for pl in planos_ativos}
            plano_pontos_label = st.selectbox("Plano a editar", list(mapa_planos), key="plano_editar_pontos")
            plano_pontos_id = mapa_planos[plano_pontos_label]
            botao_lixeira("Planos", plano_pontos_id, plano_pontos_label)
            pontos_ativos = buscar_pontos_plano(plano_pontos_id)
            if pontos_ativos:
                mapa_pontos = {f"{pt['ordem_original'] or pt['ordem']} — {pt['descricao'] or 'Sem descrição'} (ID {pt['id']})": pt for pt in pontos_ativos}
                ponto_label = st.selectbox("Ponto existente para editar", list(mapa_pontos), key="ponto_existente_editar")
                pt_edit = mapa_pontos[ponto_label]
                botao_lixeira("Pontos dos planos", pt_edit["id"], ponto_label)
                with st.form(f"form_editar_ponto_{pt_edit['id']}"):
                    tipo_pt_edit = st.selectbox("Tipo", ["NUMERICO", "QUALITATIVO"], index=1 if "QUALIT" in (pt_edit['tipo_ponto'] or "").upper() else 0)
                    descricao_pt_edit = st.text_input("Descrição/verificação *", value=pt_edit['descricao'] or "")
                    nominal_pt_edit = st.number_input("Valor nominal", value=float(pt_edit['valor_nominal'] or 0.0), format="%.6f", disabled=(tipo_pt_edit == "QUALITATIVO"))
                    unidade_pt_edit = st.text_input("Unidade (ex.: mm, °C, V)", value=pt_edit['unidade'] or "", disabled=(tipo_pt_edit == "QUALITATIVO"))
                    tol_inf_edit = st.number_input("Tolerância inferior (desvio)", value=float(pt_edit['tolerancia_inferior'] or 0.0), format="%.6f", disabled=(tipo_pt_edit == "QUALITATIVO"))
                    tol_sup_edit = st.number_input("Tolerância superior (desvio)", value=float(pt_edit['tolerancia_superior'] or 0.0), format="%.6f", disabled=(tipo_pt_edit == "QUALITATIVO"))
                    inc_edit = st.text_input("Incerteza", value=str(pt_edit['incerteza'] or ""))
                    salvar_pt_edit = st.form_submit_button("Salvar alterações do ponto", type="primary")
                if salvar_pt_edit:
                    try:
                        executar_comando("UPDATE pontos_plano SET tipo_ponto=?, descricao=?, valor_nominal=?, unidade=?, tolerancia_inferior=?, tolerancia_superior=?, incerteza=? WHERE id=?", (tipo_pt_edit, descricao_pt_edit.strip(), None if tipo_pt_edit == "QUALITATIVO" else nominal_pt_edit, None if tipo_pt_edit == "QUALITATIVO" else (unidade_pt_edit.strip() or None), None if tipo_pt_edit == "QUALITATIVO" else tol_inf_edit, None if tipo_pt_edit == "QUALITATIVO" else tol_sup_edit, inc_edit.strip() or None, pt_edit['id']))
                        sucesso("Ponto atualizado. Isso afeta novos registros; calibrações históricas preservam os valores já copiados.")
                    except Exception as erro:
                        st.error(f"Erro ao atualizar ponto: {erro}")
            with st.form(f"form_adicionar_ponto_{plano_pontos_id}"):
                st.markdown("**Adicionar novo ponto ao plano selecionado**")
                novo_tipo_ponto = st.selectbox("Tipo do novo ponto", ["NUMERICO", "QUALITATIVO"], key=f"novo_tipo_ponto_{plano_pontos_id}")
                nova_descricao_ponto = st.text_input("Descrição/verificação do ponto *", key=f"nova_desc_{plano_pontos_id}")
                novo_nominal = st.number_input("Valor nominal", value=0.0, format="%.6f", key=f"novo_nominal_{plano_pontos_id}", disabled=(novo_tipo_ponto == "QUALITATIVO"))
                nova_unidade = st.text_input("Unidade (ex.: mm, °C, V)", key=f"nova_unidade_{plano_pontos_id}", disabled=(novo_tipo_ponto == "QUALITATIVO"))
                nova_tol_inf = st.number_input("Tolerância inferior (desvio)", value=0.0, format="%.6f", key=f"nova_tol_inf_{plano_pontos_id}", disabled=(novo_tipo_ponto == "QUALITATIVO"))
                nova_tol_sup = st.number_input("Tolerância superior (desvio)", value=0.0, format="%.6f", key=f"nova_tol_sup_{plano_pontos_id}", disabled=(novo_tipo_ponto == "QUALITATIVO"))
                nova_incerteza = st.text_input("Incerteza", key=f"nova_incerteza_{plano_pontos_id}")
                adicionar_ponto_btn = st.form_submit_button("Adicionar ponto")
            if adicionar_ponto_btn:
                try:
                    if not nova_descricao_ponto.strip():
                        st.error("Informe a descrição/verificação do ponto.")
                    else:
                        ordem_nova = max([int(pt['ordem'] or 0) for pt in pontos_ativos], default=0) + 1
                        executar_comando("INSERT INTO pontos_plano (plano_id, ordem, ordem_original, tipo_ponto, descricao, valor_nominal, unidade, tolerancia_inferior, tolerancia_superior, incerteza, ativo) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 1)", (plano_pontos_id, ordem_nova, str(ordem_nova), novo_tipo_ponto, nova_descricao_ponto.strip(), None if novo_tipo_ponto == "QUALITATIVO" else novo_nominal, None if novo_tipo_ponto == "QUALITATIVO" else (nova_unidade.strip() or None), None if novo_tipo_ponto == "QUALITATIVO" else nova_tol_inf, None if novo_tipo_ponto == "QUALITATIVO" else nova_tol_sup, nova_incerteza.strip() or None))
                        sucesso("Ponto adicionado ao plano.")
                except Exception as erro:
                    st.error(f"Erro ao adicionar ponto: {erro}")
        else:
            st.info("Cadastre um tipo e um plano para começar a adicionar pontos.")

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


            historico_status = buscar_calibracoes_equipamento(equipamento_id)
            proxima_status = converter_data(historico_status[0]["data_proxima_calibracao"]) if historico_status else None
            if (equipamento["status"] or "").upper() in ("INATIVO", "DESATIVADO"):
                st.badge("Equipamento inativo", color="gray")
            elif proxima_status and proxima_status < hoje:
                st.badge("Calibração vencida", color="red")
            elif proxima_status and proxima_status <= limite_30:
                st.badge("Próxima do vencimento", color="orange")
            elif proxima_status:
                st.badge("Calibração em dia", color="green")
            else:
                st.badge("Sem calibração", color="gray")

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
                                "ultima_visivel"
                            ]
                        ),
                    )

                    st.write(
                        "**Próxima calibração:**",
                        formatar_data(
                            equipamento[
                                "proxima_visivel"
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
                    # Preserva o vínculo original ao editar outros campos, mesmo
                    # quando o plano estiver inativo ou na lixeira.
                    plano_original = executar_consulta_unica("SELECT * FROM planos_calibracao WHERE id = ?", (equipamento["plano_id"],))
                    if plano_original:
                        plano_atual_label = f"{plano_original['nome']} (plano indisponível para novas calibrações)"
                        opcoes_planos[plano_atual_label] = plano_original
                        st.warning("O plano associado está inativo ou na lixeira. Restaure-o para criar novas calibrações.")

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
                            index=lista_planos.index(plano_atual_label) if plano_atual_label in lista_planos else None,
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
                        width="stretch",
                        disabled=not opcoes_planos,
                    )


                    if salvar_edicao and plano_edit_label is None:
                        st.error("Selecione um plano de calibração para salvar as alterações.")
                    elif salvar_edicao:

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


                            sucesso("Equipamento atualizado.")


                        except Exception as erro:

                            st.error(
                                f"Erro ao atualizar: {erro}"
                            )


                st.divider()
                botao_lixeira("Equipamentos", equipamento_id, f"{equipamento['codigo']} — {equipamento['descricao']}")


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
                        localizacao_calibracao = st.text_input(
                            "Localização durante a calibração"
                        )
                        custo_calibracao = st.number_input(
                            "Custo de calibração (R$)", min_value=0.0,
                            value=0.0, step=25.0, format="%.2f"
                        )
                        observacoes_calibracao = st.text_area("Observações")


                    criar = st.form_submit_button(
                        "Criar calibração",
                        type="primary",
                        width="stretch",
                    )


                    if criar:

                        try:

                            calibracao_id = criar_calibracao(
                                equipamento_id=equipamento_id,
                                data_calibracao=data_calibracao,
                                responsavel=(responsavel_calibracao.strip() or None),
                                resultado_final=None,
                                localizacao=(localizacao_calibracao.strip() or None),
                                custo_calibracao=custo_calibracao,
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


                            sucesso(f"Calibração #{calibracao_id} criada.")


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
                        botao_lixeira("Calibrações", calibracao_selecionada, f"Calibração #{calibracao_selecionada} — {calibracao['data_calibracao']}")

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
                                    calibracao["data_proxima_calibracao"]
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
                            resultado_visual = calibracao["resultado_final"] or "Resultado não definido"
                            cor_resultado = "red" if resultado_visual.upper().startswith("REPROVADO") else "green" if resultado_visual.upper() == "APROVADO" else "gray"
                            st.badge(resultado_visual, color=cor_resultado)

                        st.write(
                            "**Responsável pela calibração:**",
                            calibracao["responsavel"] or "Não informado",
                        )
                        st.write(
                            "**Localização da calibração:**",
                            calibracao["localizacao"] or "Não informada",
                        )
                        custo_hist = calibracao["custo_calibracao"]
                        st.write(
                            "**Custo da calibração:**",
                            f"R$ {float(custo_hist):,.2f}".replace(",", "X").replace(".", ",").replace("X", ".") if custo_hist is not None else "Não informado",
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
                            sucesso("Resultado final salvo.")
                        except Exception as erro:
                            st.error(f"Erro ao salvar resultado final: {erro}")

                    st.divider()
                    st.subheader(f"Pontos da calibração — {len(pontos)}")
                    if not pontos:
                        st.warning("Esta calibração não possui pontos registrados.")
                    else:

                        if any(p["incerteza"] in (None, "") and "QUALIT" not in (p["tipo_ponto"] or "NUMERICO").upper() for p in pontos):
                            st.warning("Há pontos numéricos sem incerteza histórica. Os valores originais foram preservados; não será usado zero nem a incerteza do plano atual. Valide o registro técnico antes de recalcular resultados.")
                        pontos_editados = []
                        with st.form(f"form_pontos_calibracao_{calibracao_selecionada}"):
                            for indice, ponto in enumerate(pontos, start=1):
                                st.markdown(f"**Ponto {ponto['ordem_original'] or indice}: {ponto['descricao'] or 'Sem descrição'}**")
                                tipo_ponto = (ponto["tipo_ponto"] or "NUMERICO").upper()
                                c1, c2, c3 = st.columns([2, 1, 2])
                                if "QUALIT" in tipo_ponto:
                                    opcoes_q = ["Pendente", "Aprovado", "Reprovado", "Não aplicável"]
                                    atual_q = ponto["resultado"] if ponto["resultado"] in opcoes_q else "Pendente"
                                    with c1:
                                        resultado_ponto = st.selectbox("Resultado qualitativo", opcoes_q, index=opcoes_q.index(atual_q), key=f"qual_{ponto['id']}")
                                    valor_encontrado = None
                                    with c2:
                                        st.write("**Nominal:** —")
                                    with c3:
                                        obs_ponto = None
                                else:
                                    nominal = ponto["valor_nominal"]
                                    valor_atual = float(ponto["valor_encontrado"]) if ponto["valor_encontrado"] is not None else float(nominal or 0.0)
                                    with c1:
                                        valor_encontrado = st.number_input(
                                            (f"Valor encontrado ({ponto['unidade']})" if ponto["unidade"] else "Valor encontrado"),
                                            value=(float(ponto["valor_encontrado"]) if ponto["valor_encontrado"] is not None else None), key=f"valor_{ponto['id']}", format="%.6f", placeholder="Digite o valor encontrado"
                                        )
                                    desvio = desvio_final_com_incerteza(valor_encontrado, nominal, ponto["incerteza"]) if valor_encontrado is not None and nominal is not None else None
                                    with c2:
                                        st.write("**Nominal:**", f"{formatar_valor(nominal)} {ponto['unidade'] or ''}".strip())
                                        st.write("**Desvio:**", f"{formatar_valor(desvio)} {ponto['unidade'] or ''}".strip() if desvio is not None else "—")
                                    resultado_ponto = calcular_resultado_ponto(ponto, valor_encontrado)
                                    with c3:
                                        obs_ponto = None
                                pontos_editados.append({"id": ponto["id"], "valor_encontrado": valor_encontrado, "resultado": resultado_ponto, "observacoes": obs_ponto})
                                st.divider()
                            salvar_pontos = st.form_submit_button("Salvar valores encontrados", type="primary", width="stretch")
                        if salvar_pontos:
                            try:
                                if any(p["resultado"] == "Não avaliado: incerteza ausente" for p in pontos_editados):
                                    raise ValueError("Operação bloqueada: há valores que exigem incerteza histórica ausente. Nenhum resultado foi alterado.")
                                salvar_pontos_calibracao(calibracao_selecionada, pontos_editados)
                                sucesso("Valores encontrados, desvios e resultados salvos no histórico.")
                            except Exception as erro:
                                st.error(f"Não foi possível salvar os pontos: {erro}")

                        # Histórico legível: permanece disponível ao reabrir a calibração.
                        linhas_pontos = []
                        for indice, ponto in enumerate(pontos, start=1):
                            tipo_ponto = (ponto["tipo_ponto"] or "NUMERICO").upper()
                            nominal = ponto["valor_nominal"]
                            encontrado = ponto["valor_encontrado"]
                            desvio = desvio_final_com_incerteza(encontrado, nominal, ponto["incerteza"]) if encontrado is not None and nominal is not None and "QUALIT" not in tipo_ponto else None
                            unidade = ponto["unidade"] or ""
                            linhas_pontos.append({
                                "Verificação / descrição": ponto["descricao"] or "-",
                                "Nominal": f"{formatar_valor(nominal)} {unidade}".strip() if nominal is not None else "-",
                                "Valor encontrado": f"{formatar_valor(encontrado)} {unidade}".strip() if encontrado is not None else (ponto["resultado"] or "Pendente" if "QUALIT" in tipo_ponto else "Não informado"),
                                "Desvio": f"{formatar_valor(desvio)} {unidade}".strip() if desvio is not None else "—",
                                "Tolerância inferior": f"{formatar_valor(ponto['tolerancia_inferior'])} {unidade}".strip() if ponto["tolerancia_inferior"] is not None else "-",
                                "Tolerância superior": f"{formatar_valor(ponto['tolerancia_superior'])} {unidade}".strip() if ponto["tolerancia_superior"] is not None else "-",
                                "Incerteza": f"{ponto['incerteza']} {unidade}".strip() if ponto["incerteza"] not in (None, "") else "-",
                                "Resultado": ponto["resultado"] or "Pendente",
                            })
                        st.dataframe(tabela_status(pd.DataFrame(linhas_pontos)), width="stretch", hide_index=True)

                    st.divider()
                    st.subheader("Gráfico de tendência do equipamento")

                    if st.button("Gerar gráfico de tendência", key=f"gerar_grafico_{equipamento_id}", type="primary"):
                        conexao_grafico = conectar()
                        try:
                            dados_grafico = conexao_grafico.execute(
                                """SELECT c.data_calibracao, pc.ordem_original, pc.descricao, pc.valor_nominal,
                                          pc.valor_encontrado, pc.unidade, pc.tolerancia_inferior, pc.tolerancia_superior,
                                          pc.tipo_ponto, pc.incerteza
                                   FROM calibracoes c JOIN pontos_calibracao pc ON pc.calibracao_id = c.id
                                   WHERE c.equipamento_id = ? AND c.excluido_em IS NULL AND pc.valor_encontrado IS NOT NULL
                                     AND pc.valor_nominal IS NOT NULL
                                     AND UPPER(COALESCE(pc.tipo_ponto, 'NUMERICO')) NOT LIKE '%QUALITATIVO%'
                                   ORDER BY c.data_calibracao, c.id, pc.ordem, pc.id""",
                                (equipamento_id,),
                            ).fetchall()
                        finally:
                            conexao_grafico.close()
                        if not dados_grafico:
                            st.warning("Ainda não existem valores numéricos encontrados suficientes para gerar o gráfico.")
                        else:
                            fig, ax = plt.subplots(figsize=(11, 6))
                            grupos = {}
                            omitidos = sum(1 for reg in dados_grafico if reg["incerteza"] in (None, ""))
                            if omitidos:
                                st.warning(f"{omitidos} ponto(s) sem incerteza histórica não foram representados no gráfico. Não foram substituídos por zero.")
                            for reg in dados_grafico:
                                if reg["incerteza"] in (None, ""):
                                    continue
                                chave = (reg["ordem_original"] or reg["descricao"] or "Ponto", reg["descricao"] or "")
                                grupos.setdefault(chave, []).append(reg)
                            for (ordem, descricao), registros in grupos.items():
                                xs = [datetime.strptime(r["data_calibracao"][:10], "%Y-%m-%d") for r in registros]
                                ys = [desvio_final_com_incerteza(r["valor_encontrado"], r["valor_nominal"], r["incerteza"]) for r in registros]
                                label = f"Ponto {ordem} — {descricao}" if descricao else f"Ponto {ordem}"
                                linha, = ax.plot(xs, ys, marker="o", linewidth=2, label=label)
                                cor = linha.get_color()
                                # Os limites são desvios relativos ao nominal.
                                inferior = next((float(r["tolerancia_inferior"]) for r in registros if r["tolerancia_inferior"] is not None), None)
                                superior = next((float(r["tolerancia_superior"]) for r in registros if r["tolerancia_superior"] is not None), None)
                                if inferior is not None:
                                    ax.axhline(inferior, color=cor, linestyle="--", alpha=0.45)
                                if superior is not None:
                                    ax.axhline(superior, color=cor, linestyle="--", alpha=0.45)
                                for x, y, reg in zip(xs, ys, registros):
                                    fora = ((inferior is not None and y < inferior) or (superior is not None and y > superior))
                                    if fora:
                                        ax.scatter([x], [y], color="red", s=85, zorder=5, edgecolors="white")
                            ax.axhline(0, color="white", linewidth=1, alpha=0.5)
                            ax.set_title(f"Tendência de calibração — {equipamento['codigo']}")
                            ax.set_xlabel("Data real da calibração")
                            ax.set_ylabel("Desvio final com incerteza")
                            ax.grid(True, alpha=0.25)
                            ax.legend(loc="best", fontsize=8)
                            fig.autofmt_xdate()
                            fig.tight_layout()
                            st.pyplot(fig, width="stretch")
                            imagem = BytesIO()
                            fig.savefig(imagem, format="png", dpi=180, bbox_inches="tight")
                            plt.close(fig)
                            st.download_button("Baixar gráfico em PNG", data=imagem.getvalue(), file_name=f"tendencia_{equipamento['codigo']}.png", mime="image/png")


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
        WHERE e.ativo = 1 AND e.excluido_em IS NULL AND c.excluido_em IS NULL
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
    if resumo_status:
        st.dataframe(
            tabela_status(pd.DataFrame([r for r in resumo_status if filtro_status_atual == "Todos" or r["Status"] == filtro_status_atual], columns=["Código", "Equipamento", "Próxima calibração", "Status"])),
            width="stretch",
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
        format_func=lambda x: ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho", "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"][int(x[5:7])-1] + "/" + x[:4],
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
                    "Situação": "FEITO" if feita else ("VENCIDA" if vencimento < hoje else "PRÓXIMAS (30 DIAS)" if vencimento <= hoje + timedelta(days=30) else "EM DIA"),
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
    pendentes = sum(1 for item in eventos_mes if item["Situação"] != "FEITO")
    total_mes = len(eventos_mes)
    c1, c2, c3 = st.columns(3)
    c1.metric("Calibrações do mês", total_mes)
    c2.metric("Feitos", feitos)
    c3.metric("Falta fazer", pendentes)

    st.subheader("Equipamentos previstos para o mês")
    if df_mes.empty:
        st.info("Não há calibrações previstas para este mês com base no histórico registrado.")
    else:
        filtro_mes = st.selectbox("Situação no mês", ["Todas", "FEITO", "VENCIDA", "PRÓXIMAS (30 DIAS)", "EM DIA"], key="cronograma_situacao_mes")
        df_filtrado = df_mes if filtro_mes == "Todas" else df_mes[df_mes["Situação"] == filtro_mes]
        st.dataframe(tabela_status(df_filtrado), width="stretch", hide_index=True)
        st.caption("Verde: realizado ou em dia · amarelo: próximo do vencimento · vermelho: vencido.")

    st.divider()
    st.subheader("Vencidas")
    df_vencidas = pd.DataFrame(vencidas_atuais, columns=["Código", "Equipamento", "Data em que deveria calibrar"])
    if df_vencidas.empty:
        st.success("Não há equipamentos vencidos no momento.")
    else:
        df_vencidas["Status"] = "Vencidas"
        st.dataframe(tabela_status(df_vencidas), width="stretch", hide_index=True)


with aba_lixeira:
    pagina_lixeira()
