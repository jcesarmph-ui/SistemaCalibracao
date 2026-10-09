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
)


# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="Sistema de Gestão de Calibração",
    page_icon="🧰",
    layout="wide",
    initial_sidebar_state="expanded",
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

    # Faixa mínima
    if valor_minimo is not None:
        if valor_numerico < float(valor_minimo):
            return "Reprovado"

    # Faixa máxima
    if valor_maximo is not None:
        if valor_numerico > float(valor_maximo):
            return "Reprovado"

    # Tolerâncias relativas ao nominal
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
        return "🟢 Aprovado"

    if resultado == "Reprovado":
        return "🔴 Reprovado"

    if resultado == "Aprovado com restrição":
        return "🟡 Aprovado com restrição"

    return "⚪ Não informado"


# ============================================================
# CABEÇALHO
# ============================================================

st.title("🧰 Sistema de Gestão de Calibração")

st.caption(
    "Controle de equipamentos, planos, calibrações, "
    "pontos de medição e cronograma."
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
        "🧰 Equipamentos",
        "📅 Cronograma",
    ]
)


# ============================================================
# ABA EQUIPAMENTOS
# ============================================================

with aba_equipamentos:

    # ========================================================
    # CADASTRO
    # ========================================================

    with st.expander(
        "➕ Cadastrar novo equipamento"
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


    # ========================================================
    # LISTA DE EQUIPAMENTOS
    # ========================================================

    st.subheader("Equipamentos")


    if not equipamentos:

        st.info(
            "Nenhum equipamento cadastrado."
        )

    else:

        busca = st.text_input(
            "🔎 Pesquisar equipamento",
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


            # =================================================
            # EQUIPAMENTO SELECIONADO
            # =================================================

            st.divider()

            st.subheader(
                f"🧰 {equipamento['codigo']} — "
                f"{equipamento['descricao']}"
            )


            aba_dados, aba_edicao, aba_calibracoes = st.tabs(
                [
                    "📋 Dados",
                    "✏️ Editar",
                    "🔧 Calibrações",
                ]
            )


            # =================================================
            # DADOS
            # =================================================

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


            # =================================================
            # EDIÇÃO
            # =================================================

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
                    "A exclusão abaixo remove o equipamento "
                    "e seu histórico de calibração."
                )


                if st.button(
                    "🗑️ Excluir equipamento",
                    key=f"excluir_{equipamento_id}",
                ):

                    confirmar = st.checkbox(
                        "Confirmo que desejo excluir este equipamento.",
                        key=(
                            f"confirmar_exclusao_"
                            f"{equipamento_id}"
                        ),
                    )


                    if confirmar:

                        try:

                            conexao = conectar()


                            try:

                                calibracoes = conexao.execute(
                                    """
                                    SELECT id
                                    FROM calibracoes
                                    WHERE equipamento_id = ?
                                    """,
                                    (equipamento_id,),
                                ).fetchall()


                                for calibracao in calibracoes:

                                    conexao.execute(
                                        """
                                        DELETE FROM pontos_calibracao
                                        WHERE calibracao_id = ?
                                        """,
                                        (calibracao["id"],),
                                    )


                                conexao.execute(
                                    """
                                    DELETE FROM calibracoes
                                    WHERE equipamento_id = ?
                                    """,
                                    (equipamento_id,),
                                )


                                conexao.execute(
                                    """
                                    DELETE FROM equipamentos
                                    WHERE id = ?
                                    """,
                                    (equipamento_id,),
                                )


                                conexao.commit()


                            except Exception:

                                conexao.rollback()

                                raise


                            finally:

                                conexao.close()


                            st.success(
                                "Equipamento excluído."
                            )

                            st.rerun()


                        except Exception as erro:

                            st.error(
                                f"Erro ao excluir equipamento: {erro}"
                            )


            # =================================================
            # CALIBRAÇÕES
            # =================================================

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

                        laboratorio = st.text_input(
                            "Laboratório"
                        )


                    with col2:

                        certificado = st.text_input(
                            "Certificado"
                        )

                        observacoes_calibracao = st.text_area(
                            "Observações"
                        )


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
                            calibracao["resultado"]
                            or "Não informado"
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


                    # =========================================
                    # INFORMAÇÕES DA CALIBRAÇÃO
                    # =========================================

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
                                "**Resultado:**",
                                texto_resultado(
                                    calibracao[
                                        "resultado"
                                    ]
                                ),
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


                    # =========================================
                    # PONTOS DE CALIBRAÇÃO
                    # =========================================

                    st.divider()


                    st.subheader(
                        f"Pontos da calibração "
                        f"({len(pontos)})"
                    )


                    if not pontos:

                        st.warning(
                            "Esta calibração não possui "
                            "pontos registrados."
                        )

                    else:

                        # -------------------------------------
                        # COMBOBOX DOS PONTOS NOMINAIS
                        # -------------------------------------

                        opcoes_pontos = {}


                        for indice, ponto in enumerate(
                            pontos,
                            start=1,
                        ):

                            numero = (
                                ponto["ordem_original"]
                                or indice
                            )


                            nominal = formatar_valor(
                                ponto[
                                    "valor_nominal"
                                ]
                            )


                            unidade = (
                                ponto["unidade"]
                                or ""
                            )


                            descricao = (
                                ponto["descricao"]
                                or ""
                            )


                            label = (
                                f"Ponto {numero} — "
                                f"Nominal: {nominal}"
                            )


                            if unidade:

                                label += (
                                    f" {unidade}"
                                )


                            if descricao:

                                label += (
                                    f" — {descricao}"
                                )


                            opcoes_pontos[
                                label
                            ] = ponto["id"]


                        ids_pontos = list(
                            opcoes_pontos.values()
                        )


                        chave_ponto = (
                            f"ponto_selecionado_"
                            f"{calibracao_selecionada}"
                        )


                        ponto_atual = (
                            st.session_state.get(
                                chave_ponto
                            )
                        )


                        if (
                            ponto_atual
                            not in ids_pontos
                        ):

                            ponto_atual = ids_pontos[0]


                        ponto_selecionado_id = (
                            st.selectbox(
                                "Selecione o ponto nominal",
                                ids_pontos,
                                index=ids_pontos.index(
                                    ponto_atual
                                ),
                                format_func=lambda ponto_id: next(
                                    label
                                    for label, pid
                                    in opcoes_pontos.items()
                                    if pid == ponto_id
                                ),
                            )
                        )


                        st.session_state[
                            chave_ponto
                        ] = ponto_selecionado_id


                        ponto = next(
                            p
                            for p in pontos
                            if p["id"]
                            == ponto_selecionado_id
                        )


                        # =====================================
                        # EXIBIÇÃO DO PONTO SELECIONADO
                        # =====================================

                        st.divider()


                        numero_ponto = (
                            ponto["ordem_original"]
                            or (
                                pontos.index(
                                    ponto
                                ) + 1
                            )
                        )


                        st.markdown(
                            f"### Ponto {numero_ponto}"
                        )


                        if ponto["secao"]:

                            st.caption(
                                f"Seção: {ponto['secao']}"
                            )


                        st.write(
                            ponto["descricao"]
                            or "Sem descrição"
                        )


                        col1, col2, col3 = (
                            st.columns(3)
                        )


                        with col1:

                            st.write(
                                "**Valor nominal:**",
                                formatar_valor(
                                    ponto[
                                        "valor_nominal"
                                    ]
                                ),
                            )


                            st.write(
                                "**Unidade:**",
                                ponto[
                                    "unidade"
                                ] or "-",
                            )


                        with col2:

                            if (
                                ponto[
                                    "valor_minimo"
                                ]
                                is not None
                                or ponto[
                                    "valor_maximo"
                                ]
                                is not None
                            ):

                                st.write(
                                    "**Faixa:**",
                                    (
                                        f"{formatar_valor(ponto['valor_minimo'])}"
                                        f" a "
                                        f"{formatar_valor(ponto['valor_maximo'])}"
                                    ),
                                )

                            else:

                                st.write(
                                    "**Tolerância:**",
                                    (
                                        f"{formatar_valor(ponto['tolerancia_inferior'])}"
                                        f" / "
                                        f"{formatar_valor(ponto['tolerancia_superior'])}"
                                    ),
                                )


                        with col3:

                            st.write(
                                "**Critério:**",
                                ponto[
                                    "criterio"
                                ] or "-",
                            )


                        # =====================================
                        # VALOR ENCONTRADO
                        # =====================================

                        valor_atual = (
                            ponto[
                                "valor_encontrado"
                            ]
                        )


                        tipo_ponto = str(
                            ponto[
                                "tipo_ponto"
                            ]
                            or ""
                        ).upper()


                        st.divider()


                        dados_ponto = {}


                        if tipo_ponto in (
                            "NUMERICO",
                            "NUMÉRICO",
                            "NUMERICA",
                            "NUMÉRICA",
                        ):

                            valor_default = None


                            if valor_atual is not None:

                                try:

                                    valor_default = float(
                                        valor_atual
                                    )

                                except Exception:

                                    valor_default = None


                            valor = st.number_input(
                                "Valor encontrado",
                                value=valor_default,
                                placeholder=(
                                    "Digite o valor medido"
                                ),
                                format="%.6f",
                                key=(
                                    f"valor_"
                                    f"{calibracao_selecionada}_"
                                    f"{ponto['id']}"
                                ),
                            )


                            resultado = (
                                calcular_resultado_ponto(
                                    ponto,
                                    valor,
                                )
                            )


                            st.write(
                                "Resultado:",
                                texto_resultado(
                                    resultado
                                ),
                            )


                        else:

                            valor = st.text_input(
                                "Valor encontrado",
                                value=(
                                    str(
                                        valor_atual
                                    )
                                    if valor_atual
                                    is not None
                                    else ""
                                ),
                                key=(
                                    f"valor_"
                                    f"{calibracao_selecionada}_"
                                    f"{ponto['id']}"
                                ),
                            )


                            resultado_atual = (
                                ponto[
                                    "resultado"
                                ]
                                or "Não informado"
                            )


                            opcoes_resultado = [
                                "Aprovado",
                                "Reprovado",
                                "Aprovado com restrição",
                                "Não informado",
                            ]


                            indice_resultado = 0


                            if (
                                resultado_atual
                                in opcoes_resultado
                            ):

                                indice_resultado = (
                                    opcoes_resultado.index(
                                        resultado_atual
                                    )
                                )


                            resultado = (
                                st.selectbox(
                                    "Resultado",
                                    opcoes_resultado,
                                    index=(
                                        indice_resultado
                                    ),
                                    key=(
                                        f"resultado_"
                                        f"{calibracao_selecionada}_"
                                        f"{ponto['id']}"
                                    ),
                                )
                            )


                        observacao_ponto = (
                            st.text_input(
                                "Observação do ponto",
                                value=(
                                    ponto[
                                        "observacoes"
                                    ] or ""
                                ),
                                key=(
                                    f"obs_"
                                    f"{calibracao_selecionada}_"
                                    f"{ponto['id']}"
                                ),
                            )
                        )


                        dados_ponto = {
                            "id": ponto["id"],
                            "valor_encontrado": valor,
                            "resultado": resultado,
                            "observacoes": (
                                observacao_ponto.strip()
                                or None
                            ),
                        }


                        # =====================================
                        # SALVAR PONTO
                        # =====================================

                        if st.button(
                            "💾 Salvar ponto",
                            type="primary",
                            use_container_width=True,
                            key=(
                                f"salvar_ponto_"
                                f"{calibracao_selecionada}_"
                                f"{ponto['id']}"
                            ),
                        ):

                            try:

                                resultado_geral = (
                                    salvar_pontos_calibracao(
                                        calibracao_selecionada,
                                        [
                                            dados_ponto
                                        ],
                                    )
                                )


                                st.success(
                                    "Ponto salvo com sucesso."
                                )


                                st.info(
                                    "Resultado geral: "
                                    + (
                                        resultado_geral
                                        or "Não informado"
                                    )
                                )


                                st.rerun()


                            except Exception as erro:

                                st.error(
                                    "Erro ao salvar ponto: "
                                    f"{erro}"
                                )


                        # =====================================
                        # RESUMO DOS PONTOS
                        # =====================================

                        st.divider()

                        st.subheader(
                            "Resumo dos pontos"
                        )


                        resumo_pontos = []


                        for indice, p in enumerate(
                            pontos,
                            start=1,
                        ):

                            resultado_ponto = (
                                p["resultado"]
                                or "Não informado"
                            )


                            resumo_pontos.append(
                                {
                                    "Ponto": (
                                        p[
                                            "ordem_original"
                                        ]
                                        or indice
                                    ),
                                    "Nominal": (
                                        formatar_valor(
                                            p[
                                                "valor_nominal"
                                            ]
                                        )
                                    ),
                                    "Unidade": (
                                        p[
                                            "unidade"
                                        ] or "-"
                                    ),
                                    "Valor encontrado": (
                                        formatar_valor(
                                            p[
                                                "valor_encontrado"
                                            ]
                                        )
                                    ),
                                    "Resultado": (
                                        resultado_ponto
                                    ),
                                }
                            )


                        st.dataframe(
                            pd.DataFrame(
                                resumo_pontos
                            ),
                            use_container_width=True,
                            hide_index=True,
                        )


# ============================================================
# ABA CRONOGRAMA
# ============================================================

with aba_cronograma:

    st.subheader(
        "📅 Cronograma de Calibração"
    )


    if not calibracoes_todas:

        st.info(
            "Ainda não existem calibrações cadastradas."
        )

    else:

        registros = []


        for calibracao in calibracoes_todas:

            data_proxima = converter_data(
                calibracao[
                    "data_proxima_calibracao"
                ]
            )


            status = "Sem data"


            if data_proxima:

                if data_proxima < hoje:

                    status = "VENCIDA"

                elif data_proxima <= (
                    hoje + timedelta(days=30)
                ):

                    status = "PRÓXIMA"

                else:

                    status = "PROGRAMADA"


            registros.append(
                {
                    "ID": calibracao["id"],
                    "Código": calibracao[
                        "equipamento_codigo"
                    ],
                    "Equipamento": calibracao[
                        "equipamento_descricao"
                    ],
                    "Tipo": calibracao[
                        "tipo_instrumento"
                    ] or "-",
                    "Última calibração": (
                        formatar_data(
                            calibracao[
                                "data_calibracao"
                            ]
                        )
                    ),
                    "Próxima calibração": (
                        formatar_data(
                            calibracao[
                                "data_proxima_calibracao"
                            ]
                        )
                    ),
                    "Laboratório": calibracao[
                        "laboratorio"
                    ] or "-",
                    "Certificado": calibracao[
                        "certificado"
                    ] or "-",
                    "Resultado": calibracao[
                        "resultado"
                    ] or "Não informado",
                    "Status": status,
                }
            )


        df_cronograma = pd.DataFrame(
            registros
        )


        # ====================================================
        # FILTROS
        # ====================================================

        col1, col2, col3 = st.columns(3)


        with col1:

            filtro_status = st.selectbox(
                "Status",
                [
                    "Todos",
                    "VENCIDA",
                    "PRÓXIMA",
                    "PROGRAMADA",
                    "Sem data",
                ],
            )


        with col2:

            meses_disponiveis = sorted(
                set(
                    converter_data(
                        c[
                            "data_proxima_calibracao"
                        ]
                    ).strftime("%m/%Y")
                    for c in calibracoes_todas
                    if converter_data(
                        c[
                            "data_proxima_calibracao"
                        ]
                    )
                )
            )


            filtro_mes = st.selectbox(
                "Mês da próxima calibração",
                ["Todos"]
                + meses_disponiveis,
            )


        with col3:

            filtro_texto = st.text_input(
                "Pesquisar equipamento"
            )


        df_filtrado = (
            df_cronograma.copy()
        )


        if filtro_status != "Todos":

            df_filtrado = df_filtrado[
                df_filtrado["Status"]
                == filtro_status
            ]


        if filtro_mes != "Todos":

            df_filtrado = df_filtrado[
                df_filtrado[
                    "Próxima calibração"
                ].str.endswith(
                    filtro_mes,
                    na=False,
                )
            ]


        if filtro_texto.strip():

            texto = (
                filtro_texto.lower()
            )


            mascara = (
                df_filtrado[
                    "Código"
                ]
                .astype(str)
                .str.lower()
                .str.contains(
                    texto,
                    na=False,
                )
                |
                df_filtrado[
                    "Equipamento"
                ]
                .astype(str)
                .str.lower()
                .str.contains(
                    texto,
                    na=False,
                )
            )


            df_filtrado = (
                df_filtrado[mascara]
            )


        st.write(
            f"**{len(df_filtrado)} registro(s)**"
        )


        st.dataframe(
            df_filtrado,
            use_container_width=True,
            hide_index=True,
            column_config={
                "ID": st.column_config.NumberColumn(
                    "ID",
                    width="small",
                ),
                "Código": st.column_config.TextColumn(
                    "Código",
                    width="small",
                ),
                "Equipamento": st.column_config.TextColumn(
                    "Equipamento",
                    width="medium",
                ),
                "Status": st.column_config.TextColumn(
                    "Status",
                    width="small",
                ),
            },
        )


        # ====================================================
        # VENCIDAS
        # ====================================================

        if vencidas:

            st.divider()

            st.subheader(
                "🔴 Calibrações vencidas"
            )


            vencidas_tabela = []


            for calibracao in vencidas:

                vencidas_tabela.append(
                    {
                        "Código": calibracao[
                            "equipamento_codigo"
                        ],
                        "Equipamento": calibracao[
                            "equipamento_descricao"
                        ],
                        "Data prevista": (
                            formatar_data(
                                calibracao[
                                    "data_proxima_calibracao"
                                ]
                            )
                        ),
                        "Certificado": calibracao[
                            "certificado"
                        ] or "-",
                    }
                )


            st.dataframe(
                pd.DataFrame(
                    vencidas_tabela
                ),
                use_container_width=True,
                hide_index=True,
            )


        # ====================================================
        # PRÓXIMOS 30 DIAS
        # ====================================================

        if proximos_30:

            st.divider()

            st.subheader(
                "🟡 Próximas calibrações — 30 dias"
            )


            proximas_tabela = []


            for calibracao in proximos_30:

                proximas_tabela.append(
                    {
                        "Código": calibracao[
                            "equipamento_codigo"
                        ],
                        "Equipamento": calibracao[
                            "equipamento_descricao"
                        ],
                        "Data prevista": (
                            formatar_data(
                                calibracao[
                                    "data_proxima_calibracao"
                                ]
                            )
                        ),
                        "Laboratório": calibracao[
                            "laboratorio"
                        ] or "-",
                    }
                )


            st.dataframe(
                pd.DataFrame(
                    proximas_tabela
                ),
                use_container_width=True,
                hide_index=True,
            )