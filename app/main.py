import streamlit as st
from datetime import date
from dateutil.relativedelta import relativedelta

from database.db import conectar, criar_banco


# ============================================================
# CONFIGURAÇÃO
# ============================================================

st.set_page_config(
    page_title="Sistema de Calibração",
    page_icon="🔧",
    layout="wide"
)

criar_banco()


# ============================================================
# FUNÇÕES - EQUIPAMENTOS
# ============================================================

def buscar_equipamentos():
    conexao = conectar()

    equipamentos = conexao.execute("""
        SELECT *
        FROM equipamentos
        ORDER BY codigo
    """).fetchall()

    conexao.close()

    return equipamentos


def cadastrar_equipamento(
    codigo,
    descricao,
    fabricante,
    modelo,
    numero_serie,
    localizacao,
    responsavel,
    periodicidade_meses,
    status,
    observacoes
):
    conexao = conectar()

    conexao.execute("""
        INSERT INTO equipamentos (
            codigo,
            descricao,
            fabricante,
            modelo,
            numero_serie,
            localizacao,
            responsavel,
            periodicidade_meses,
            status,
            observacoes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        codigo,
        descricao,
        fabricante,
        modelo,
        numero_serie,
        localizacao,
        responsavel,
        periodicidade_meses,
        status,
        observacoes
    ))

    conexao.commit()
    conexao.close()


def atualizar_equipamento(
    equipamento_id,
    codigo,
    descricao,
    fabricante,
    modelo,
    numero_serie,
    localizacao,
    responsavel,
    periodicidade_meses,
    status,
    observacoes
):
    conexao = conectar()

    conexao.execute("""
        UPDATE equipamentos
        SET
            codigo = ?,
            descricao = ?,
            fabricante = ?,
            modelo = ?,
            numero_serie = ?,
            localizacao = ?,
            responsavel = ?,
            periodicidade_meses = ?,
            status = ?,
            observacoes = ?
        WHERE id = ?
    """, (
        codigo,
        descricao,
        fabricante,
        modelo,
        numero_serie,
        localizacao,
        responsavel,
        periodicidade_meses,
        status,
        observacoes,
        equipamento_id
    ))

    conexao.commit()
    conexao.close()


def excluir_equipamento(equipamento_id):
    conexao = conectar()

    conexao.execute("""
        DELETE FROM calibracoes
        WHERE equipamento_id = ?
    """, (equipamento_id,))

    conexao.execute("""
        DELETE FROM equipamentos
        WHERE id = ?
    """, (equipamento_id,))

    conexao.commit()
    conexao.close()


# ============================================================
# FUNÇÕES - CALIBRAÇÕES
# ============================================================

def buscar_calibracoes(equipamento_id):
    conexao = conectar()

    calibracoes = conexao.execute("""
        SELECT *
        FROM calibracoes
        WHERE equipamento_id = ?
        ORDER BY data_calibracao DESC
    """, (equipamento_id,)).fetchall()

    conexao.close()

    return calibracoes


def buscar_todas_calibracoes():
    conexao = conectar()

    calibracoes = conexao.execute("""
        SELECT
            calibracoes.*,
            equipamentos.codigo,
            equipamentos.descricao,
            equipamentos.fabricante,
            equipamentos.modelo,
            equipamentos.localizacao
        FROM calibracoes
        INNER JOIN equipamentos
            ON calibracoes.equipamento_id = equipamentos.id
        ORDER BY data_proxima_calibracao
    """).fetchall()

    conexao.close()

    return calibracoes


def buscar_equipamentos_sem_calibracao():
    conexao = conectar()

    equipamentos = conexao.execute("""
        SELECT equipamentos.*
        FROM equipamentos
        LEFT JOIN calibracoes
            ON equipamentos.id = calibracoes.equipamento_id
        WHERE calibracoes.id IS NULL
        ORDER BY equipamentos.codigo
    """).fetchall()

    conexao.close()

    return equipamentos


def cadastrar_calibracao(
    equipamento_id,
    data_calibracao,
    data_proxima_calibracao,
    laboratorio,
    certificado,
    resultado,
    observacoes
):
    conexao = conectar()

    cursor = conexao.execute("""
        INSERT INTO calibracoes (
            equipamento_id,
            data_calibracao,
            data_proxima_calibracao,
            laboratorio,
            certificado,
            resultado,
            observacoes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """, (
        equipamento_id,
        data_calibracao,
        data_proxima_calibracao,
        laboratorio,
        certificado,
        resultado,
        observacoes
    ))

    calibracao_id = cursor.lastrowid

    conexao.commit()
    conexao.close()

    return calibracao_id


# ============================================================
# FUNÇÕES - PONTOS DE CALIBRAÇÃO
# ============================================================

def buscar_pontos_calibracao(calibracao_id):
    conexao = conectar()

    pontos = conexao.execute("""
        SELECT *
        FROM pontos_calibracao
        WHERE calibracao_id = ?
        ORDER BY ponto_nominal
    """, (calibracao_id,)).fetchall()

    conexao.close()

    return pontos


def cadastrar_ponto_calibracao(
    calibracao_id,
    ponto_nominal,
    valor_encontrado,
    unidade,
    tolerancia_inferior,
    tolerancia_superior,
    resultado,
    observacoes
):
    conexao = conectar()

    conexao.execute("""
        INSERT INTO pontos_calibracao (
            calibracao_id,
            ponto_nominal,
            valor_encontrado,
            unidade,
            tolerancia_inferior,
            tolerancia_superior,
            resultado,
            observacoes
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        calibracao_id,
        ponto_nominal,
        valor_encontrado,
        unidade,
        tolerancia_inferior,
        tolerancia_superior,
        resultado,
        observacoes
    ))

    conexao.commit()
    conexao.close()


def excluir_ponto_calibracao(ponto_id):
    conexao = conectar()

    conexao.execute("""
        DELETE FROM pontos_calibracao
        WHERE id = ?
    """, (ponto_id,))

    conexao.commit()
    conexao.close()


# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================

def converter_data(data_texto):
    if not data_texto:
        return None

    try:
        return date.fromisoformat(data_texto)
    except ValueError:
        return None


def formatar_data(data_texto):
    data_convertida = converter_data(data_texto)

    if data_convertida is None:
        return "-"

    return data_convertida.strftime("%d/%m/%Y")


def obter_status_calibracao(data_proxima):
    hoje = date.today()

    if data_proxima is None:
        return "Sem data"

    if data_proxima < hoje:
        return "Vencida"

    if data_proxima == hoje:
        return "Vence hoje"

    limite_30_dias = hoje + relativedelta(days=30)

    if data_proxima <= limite_30_dias:
        return "Próxima"

    return "Em dia"


def obter_cor_status(status):
    if status == "Vencida":
        return "🔴"

    if status == "Vence hoje":
        return "🟠"

    if status == "Próxima":
        return "🟡"

    if status == "Em dia":
        return "🟢"

    return "⚪"


def calcular_resultado_ponto(
    valor_encontrado,
    tolerancia_inferior,
    tolerancia_superior
):
    if valor_encontrado is None:
        return "Não informado"

    if tolerancia_inferior is None:
        return "Não avaliado"

    if tolerancia_superior is None:
        return "Não avaliado"

    if (
        tolerancia_inferior
        <= valor_encontrado
        <= tolerancia_superior
    ):
        return "Aprovado"

    return "Reprovado"


# ============================================================
# CABEÇALHO
# ============================================================

st.title("🔧 Sistema de Calibração")

st.caption(
    "Controle de equipamentos, calibrações e cronograma"
)


# ============================================================
# CARREGAMENTO DOS DADOS
# ============================================================

equipamentos = buscar_equipamentos()
calibracoes = buscar_todas_calibracoes()
equipamentos_sem_calibracao = buscar_equipamentos_sem_calibracao()

hoje = date.today()


# ============================================================
# INDICADORES
# ============================================================

calibracoes_validas = []

for calibracao in calibracoes:

    data_proxima = converter_data(
        calibracao["data_proxima_calibracao"]
    )

    if data_proxima:
        calibracoes_validas.append(
            (calibracao, data_proxima)
        )


vencidas = [
    item
    for item in calibracoes_validas
    if item[1] < hoje
]


proximos_30_dias = [
    item
    for item in calibracoes_validas
    if hoje <= item[1] <= hoje + relativedelta(days=30)
]


col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    st.metric("Equipamentos", len(equipamentos))

with col2:
    st.metric("Calibrações", len(calibracoes))

with col3:
    st.metric("Vencidas", len(vencidas))

with col4:
    st.metric("Próximos 30 dias", len(proximos_30_dias))

with col5:
    st.metric(
        "Sem calibração",
        len(equipamentos_sem_calibracao)
    )


st.divider()


# ============================================================
# ABAS PRINCIPAIS
# ============================================================

aba_equipamentos, aba_cronograma = st.tabs([
    "🔧 Equipamentos",
    "📅 Cronograma de Calibração"
])


# ============================================================
# ABA EQUIPAMENTOS
# ============================================================

with aba_equipamentos:

    st.header("Equipamentos")


    # ========================================================
    # CADASTRO
    # ========================================================

    with st.expander("➕ Cadastrar novo equipamento"):

        with st.form("form_cadastro_equipamento"):

            col1, col2 = st.columns(2)

            with col1:

                codigo = st.text_input(
                    "Código*",
                    placeholder="Ex.: EQ-001"
                )

                descricao = st.text_input(
                    "Descrição*",
                    placeholder="Ex.: Paquímetro"
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

                localizacao = st.text_input(
                    "Localização"
                )

                responsavel = st.text_input(
                    "Responsável"
                )

                periodicidade_meses = st.number_input(
                    "Periodicidade da calibração (meses)",
                    min_value=1,
                    value=12,
                    step=1
                )

                status = st.selectbox(
                    "Status",
                    [
                        "Ativo",
                        "Inativo",
                        "Em manutenção"
                    ]
                )

                observacoes = st.text_area(
                    "Observações"
                )


            cadastrar = st.form_submit_button(
                "Cadastrar equipamento"
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

                        cadastrar_equipamento(
                            codigo.strip(),
                            descricao.strip(),
                            fabricante.strip(),
                            modelo.strip(),
                            numero_serie.strip(),
                            localizacao.strip(),
                            responsavel.strip(),
                            periodicidade_meses,
                            status,
                            observacoes.strip()
                        )

                        st.success(
                            "Equipamento cadastrado com sucesso!"
                        )

                        st.rerun()

                    except Exception as erro:

                        st.error(
                            f"Erro ao cadastrar equipamento: {erro}"
                        )


    # ========================================================
    # LISTAGEM
    # ========================================================

    if not equipamentos:

        st.info(
            "Nenhum equipamento cadastrado."
        )

    else:

        for equipamento in equipamentos:

            titulo = (
                f"{equipamento['codigo']} — "
                f"{equipamento['descricao']}"
            )

            with st.expander(titulo):

                aba_detalhes, aba_editar, aba_calibracoes = st.tabs([
                    "Detalhes",
                    "Editar",
                    "Calibrações"
                ])


                # ============================================
                # DETALHES
                # ============================================

                with aba_detalhes:

                    col1, col2 = st.columns(2)

                    with col1:

                        st.write(
                            f"**Código:** {equipamento['codigo']}"
                        )

                        st.write(
                            f"**Descrição:** {equipamento['descricao']}"
                        )

                        st.write(
                            f"**Fabricante:** "
                            f"{equipamento['fabricante'] or '-'}"
                        )

                        st.write(
                            f"**Modelo:** "
                            f"{equipamento['modelo'] or '-'}"
                        )

                        st.write(
                            f"**Número de série:** "
                            f"{equipamento['numero_serie'] or '-'}"
                        )

                    with col2:

                        st.write(
                            f"**Localização:** "
                            f"{equipamento['localizacao'] or '-'}"
                        )

                        st.write(
                            f"**Responsável:** "
                            f"{equipamento['responsavel'] or '-'}"
                        )

                        st.write(
                            f"**Periodicidade:** "
                            f"{equipamento['periodicidade_meses']} meses"
                        )

                        st.write(
                            f"**Status:** "
                            f"{equipamento['status']}"
                        )

                    if equipamento["observacoes"]:

                        st.write(
                            f"**Observações:** "
                            f"{equipamento['observacoes']}"
                        )


                # ============================================
                # EDITAR
                # ============================================

                with aba_editar:

                    with st.form(
                        f"form_editar_{equipamento['id']}"
                    ):

                        col1, col2 = st.columns(2)

                        with col1:

                            novo_codigo = st.text_input(
                                "Código",
                                value=equipamento["codigo"]
                            )

                            nova_descricao = st.text_input(
                                "Descrição",
                                value=equipamento["descricao"]
                            )

                            novo_fabricante = st.text_input(
                                "Fabricante",
                                value=equipamento["fabricante"] or ""
                            )

                            novo_modelo = st.text_input(
                                "Modelo",
                                value=equipamento["modelo"] or ""
                            )

                            novo_numero_serie = st.text_input(
                                "Número de série",
                                value=equipamento["numero_serie"] or ""
                            )

                        with col2:

                            nova_localizacao = st.text_input(
                                "Localização",
                                value=equipamento["localizacao"] or ""
                            )

                            novo_responsavel = st.text_input(
                                "Responsável",
                                value=equipamento["responsavel"] or ""
                            )

                            nova_periodicidade = st.number_input(
                                "Periodicidade (meses)",
                                min_value=1,
                                value=equipamento["periodicidade_meses"] or 12,
                                step=1
                            )

                            novo_status = st.selectbox(
                                "Status",
                                [
                                    "Ativo",
                                    "Inativo",
                                    "Em manutenção"
                                ],
                                index=[
                                    "Ativo",
                                    "Inativo",
                                    "Em manutenção"
                                ].index(equipamento["status"])
                                if equipamento["status"]
                                in [
                                    "Ativo",
                                    "Inativo",
                                    "Em manutenção"
                                ]
                                else 0
                            )

                            novas_observacoes = st.text_area(
                                "Observações",
                                value=equipamento["observacoes"] or ""
                            )


                        salvar = st.form_submit_button(
                            "Salvar alterações"
                        )


                        if salvar:

                            try:

                                atualizar_equipamento(
                                    equipamento["id"],
                                    novo_codigo.strip(),
                                    nova_descricao.strip(),
                                    novo_fabricante.strip(),
                                    novo_modelo.strip(),
                                    novo_numero_serie.strip(),
                                    nova_localizacao.strip(),
                                    novo_responsavel.strip(),
                                    nova_periodicidade,
                                    novo_status,
                                    novas_observacoes.strip()
                                )

                                st.success(
                                    "Equipamento atualizado com sucesso!"
                                )

                                st.rerun()

                            except Exception as erro:

                                st.error(
                                    f"Erro ao atualizar: {erro}"
                                )


                    st.divider()


                    excluir = st.button(
                        "🗑️ Excluir equipamento",
                        key=f"excluir_{equipamento['id']}"
                    )


                    if excluir:

                        excluir_equipamento(
                            equipamento["id"]
                        )

                        st.success(
                            "Equipamento excluído com sucesso!"
                        )

                        st.rerun()


                # ============================================
                # CALIBRAÇÕES
                # ============================================

                with aba_calibracoes:

                    st.subheader(
                        "Histórico de calibrações"
                    )


                    with st.form(
                        f"form_calibracao_{equipamento['id']}"
                    ):

                        data_calibracao = st.date_input(
                            "Data da calibração",
                            value=date.today()
                        )


                        data_proxima_calibracao = (
                            data_calibracao
                            + relativedelta(
                                months=equipamento[
                                    "periodicidade_meses"
                                ]
                            )
                        )


                        st.info(
                            "📅 Próxima calibração calculada: "
                            f"**{data_proxima_calibracao.strftime('%d/%m/%Y')}**"
                        )


                        laboratorio = st.text_input(
                            "Laboratório"
                        )

                        certificado = st.text_input(
                            "Número do certificado"
                        )

                        resultado = st.selectbox(
                            "Resultado",
                            [
                                "Aprovado",
                                "Aprovado com restrição",
                                "Reprovado"
                            ]
                        )

                        observacoes_calibracao = st.text_area(
                            "Observações"
                        )


                        cadastrar_cal = st.form_submit_button(
                            "Cadastrar calibração"
                        )


                        if cadastrar_cal:

                            cadastrar_calibracao(
                                equipamento["id"],
                                data_calibracao.isoformat(),
                                data_proxima_calibracao.isoformat(),
                                laboratorio.strip(),
                                certificado.strip(),
                                resultado,
                                observacoes_calibracao.strip()
                            )

                            st.success(
                                "Calibração cadastrada com sucesso!"
                            )

                            st.rerun()


                    st.divider()


                    historico = buscar_calibracoes(
                        equipamento["id"]
                    )


                    if not historico:

                        st.info(
                            "Nenhuma calibração registrada "
                            "para este equipamento."
                        )

                    else:

                        for calibracao in historico:

                            data_proxima = converter_data(
                                calibracao[
                                    "data_proxima_calibracao"
                                ]
                            )

                            status_calibracao = (
                                obter_status_calibracao(
                                    data_proxima
                                )
                            )

                            icone_status = obter_cor_status(
                                status_calibracao
                            )


                            with st.expander(
                                f"{icone_status} "
                                f"Calibração de "
                                f"{formatar_data(calibracao['data_calibracao'])}"
                            ):

                                col1, col2 = st.columns(2)

                                with col1:

                                    st.write(
                                        f"**Laboratório:** "
                                        f"{calibracao['laboratorio'] or '-'}"
                                    )

                                    st.write(
                                        f"**Certificado:** "
                                        f"{calibracao['certificado'] or '-'}"
                                    )

                                    st.write(
                                        f"**Data:** "
                                        f"{formatar_data(calibracao['data_calibracao'])}"
                                    )

                                    st.write(
                                        f"**Próxima:** "
                                        f"{formatar_data(calibracao['data_proxima_calibracao'])}"
                                    )

                                with col2:

                                    st.write(
                                        f"**Status:** "
                                        f"{icone_status} "
                                        f"{status_calibracao}"
                                    )

                                    st.write(
                                        f"**Resultado:** "
                                        f"{calibracao['resultado'] or '-'}"
                                    )

                                    st.write(
                                        f"**Observações:** "
                                        f"{calibracao['observacoes'] or '-'}"
                                    )


                                st.divider()


                                # ====================================
                                # PONTOS DE CALIBRAÇÃO
                                # ====================================

                                st.subheader(
                                    "📏 Pontos de calibração"
                                )

                                pontos = buscar_pontos_calibracao(
                                    calibracao["id"]
                                )


                                # -------------------------------
                                # CADASTRO DE PONTO
                                # -------------------------------

                                with st.form(
                                    f"form_ponto_{calibracao['id']}"
                                ):

                                    col1, col2, col3 = st.columns(3)

                                    with col1:

                                        ponto_nominal = st.number_input(
                                            "Ponto nominal",
                                            value=0.0,
                                            format="%.6f"
                                        )

                                        unidade = st.text_input(
                                            "Unidade",
                                            placeholder="mm, kg, °C..."
                                        )

                                    with col2:

                                        valor_encontrado = st.number_input(
                                            "Valor encontrado",
                                            value=0.0,
                                            format="%.6f"
                                        )

                                        tolerancia_inferior = st.number_input(
                                            "Limite inferior",
                                            value=0.0,
                                            format="%.6f"
                                        )

                                    with col3:

                                        tolerancia_superior = st.number_input(
                                            "Limite superior",
                                            value=0.0,
                                            format="%.6f"
                                        )

                                        observacoes_ponto = st.text_input(
                                            "Observações"
                                        )


                                    resultado_ponto = calcular_resultado_ponto(
                                        valor_encontrado,
                                        tolerancia_inferior,
                                        tolerancia_superior
                                    )


                                    st.info(
                                        f"Resultado calculado: "
                                        f"**{resultado_ponto}**"
                                    )


                                    cadastrar_ponto = (
                                        st.form_submit_button(
                                            "Adicionar ponto"
                                        )
                                    )


                                    if cadastrar_ponto:

                                        cadastrar_ponto_calibracao(
                                            calibracao["id"],
                                            ponto_nominal,
                                            valor_encontrado,
                                            unidade.strip(),
                                            tolerancia_inferior,
                                            tolerancia_superior,
                                            resultado_ponto,
                                            observacoes_ponto.strip()
                                        )

                                        st.success(
                                            "Ponto de calibração "
                                            "adicionado com sucesso!"
                                        )

                                        st.rerun()


                                # -------------------------------
                                # LISTAGEM DOS PONTOS
                                # -------------------------------

                                if not pontos:

                                    st.info(
                                        "Nenhum ponto cadastrado "
                                        "para esta calibração."
                                    )

                                else:

                                    dados_pontos = []

                                    for ponto in pontos:

                                        dados_pontos.append({
                                            "Ponto nominal": ponto[
                                                "ponto_nominal"
                                            ],
                                            "Valor encontrado": ponto[
                                                "valor_encontrado"
                                            ],
                                            "Unidade": ponto[
                                                "unidade"
                                            ] or "-",
                                            "Limite inferior": ponto[
                                                "tolerancia_inferior"
                                            ],
                                            "Limite superior": ponto[
                                                "tolerancia_superior"
                                            ],
                                            "Resultado": ponto[
                                                "resultado"
                                            ],
                                            "Observações": ponto[
                                                "observacoes"
                                            ] or "-"
                                        })


                                    st.dataframe(
                                        dados_pontos,
                                        use_container_width=True,
                                        hide_index=True
                                    )


                                    st.markdown(
                                        "**Excluir ponto:**"
                                    )


                                    for ponto in pontos:

                                        if st.button(
                                            f"🗑️ Ponto "
                                            f"{ponto['ponto_nominal']}",
                                            key=(
                                                f"excluir_ponto_"
                                                f"{ponto['id']}"
                                            )
                                        ):

                                            excluir_ponto_calibracao(
                                                ponto["id"]
                                            )

                                            st.rerun()


# ============================================================
# ABA CRONOGRAMA
# ============================================================

with aba_cronograma:

    st.header("📅 Cronograma de Calibração")

    st.write(
        "Acompanhe as calibrações vencidas, atuais e futuras."
    )


    # ========================================================
    # EQUIPAMENTOS SEM CALIBRAÇÃO
    # ========================================================

    if equipamentos_sem_calibracao:

        st.warning(
            f"⚠️ Existem {len(equipamentos_sem_calibracao)} "
            "equipamento(s) sem nenhuma calibração registrada."
        )

        with st.expander(
            "Ver equipamentos sem calibração"
        ):

            for equipamento in equipamentos_sem_calibracao:

                st.write(
                    f"**{equipamento['codigo']}** — "
                    f"{equipamento['descricao']} "
                    f"— Local: "
                    f"{equipamento['localizacao'] or '-'}"
                )


    # ========================================================
    # FILTRO DE PERÍODO
    # ========================================================

    st.subheader("🔎 Consultar período")

    col1, col2 = st.columns(2)

    meses = [
        "Janeiro",
        "Fevereiro",
        "Março",
        "Abril",
        "Maio",
        "Junho",
        "Julho",
        "Agosto",
        "Setembro",
        "Outubro",
        "Novembro",
        "Dezembro"
    ]

    with col1:

        mes_selecionado = st.selectbox(
            "Mês",
            range(1, 13),
            index=hoje.month - 1,
            format_func=lambda numero: meses[numero - 1]
        )

    with col2:

        ano_selecionado = st.number_input(
            "Ano",
            min_value=2023,
            max_value=2100,
            value=hoje.year,
            step=1
        )


    # ========================================================
    # DADOS DO CRONOGRAMA
    # ========================================================

    registros_cronograma = []

    for calibracao in calibracoes:

        data_proxima = converter_data(
            calibracao["data_proxima_calibracao"]
        )

        if data_proxima:

            registros_cronograma.append({
                "codigo": calibracao["codigo"],
                "descricao": calibracao["descricao"],
                "localizacao": calibracao["localizacao"],
                "data_calibracao": converter_data(
                    calibracao["data_calibracao"]
                ),
                "data_proxima": data_proxima,
                "status": obter_status_calibracao(
                    data_proxima
                ),
                "laboratorio": calibracao["laboratorio"],
                "certificado": calibracao["certificado"]
            })


    registros_cronograma.sort(
        key=lambda item: item["data_proxima"]
    )


    # ========================================================
    # CALIBRAÇÕES DO MÊS
    # ========================================================

    registros_mes = [
        item
        for item in registros_cronograma
        if (
            item["data_proxima"].month == mes_selecionado
            and item["data_proxima"].year == ano_selecionado
        )
    ]


    st.divider()

    st.subheader(
        f"📋 Calibrações de "
        f"{meses[mes_selecionado - 1]} "
        f"de {ano_selecionado}"
    )


    if not registros_mes:

        st.info(
            "Nenhuma calibração prevista para este mês."
        )

    else:

        for item in registros_mes:

            dias = (
                item["data_proxima"] - hoje
            ).days

            icone = obter_cor_status(
                item["status"]
            )

            if dias < 0:

                prazo = (
                    f"Vencida há {abs(dias)} dias"
                )

            elif dias == 0:

                prazo = "Vence hoje"

            else:

                prazo = (
                    f"Faltam {dias} dias"
                )


            st.markdown(
                f"""
                ### {icone} {item['codigo']} — {item['descricao']}

                **Data da próxima calibração:** {
                    item['data_proxima'].strftime('%d/%m/%Y')
                }

                **Status:** {item['status']}

                **Prazo:** {prazo}

                **Localização:** {
                    item['localizacao'] or '-'
                }

                **Laboratório:** {
                    item['laboratorio'] or '-'
                }

                **Certificado:** {
                    item['certificado'] or '-'
                }
                """
            )

            st.divider()


    # ========================================================
    # VENCIDAS
    # ========================================================

    st.subheader("🔴 Calibrações vencidas")

    registros_vencidos = [
        item
        for item in registros_cronograma
        if item["data_proxima"] < hoje
    ]


    if not registros_vencidos:

        st.success(
            "Nenhuma calibração vencida."
        )

    else:

        tabela_vencidas = []

        for item in registros_vencidos:

            dias_atraso = (
                hoje - item["data_proxima"]
            ).days

            tabela_vencidas.append({
                "Código": item["codigo"],
                "Equipamento": item["descricao"],
                "Data prevista": item[
                    "data_proxima"
                ].strftime("%d/%m/%Y"),
                "Dias em atraso": dias_atraso,
                "Localização": item["localizacao"] or "-"
            })


        st.dataframe(
            tabela_vencidas,
            use_container_width=True,
            hide_index=True
        )


    # ========================================================
    # PRÓXIMOS 30 DIAS
    # ========================================================

    st.subheader("🟡 Próximos 30 dias")

    registros_30_dias = [
        item
        for item in registros_cronograma
        if (
            hoje <= item["data_proxima"]
            <= hoje + relativedelta(days=30)
        )
    ]


    if not registros_30_dias:

        st.success(
            "Nenhuma calibração prevista "
            "para os próximos 30 dias."
        )

    else:

        tabela_30_dias = []

        for item in registros_30_dias:

            dias = (
                item["data_proxima"] - hoje
            ).days

            tabela_30_dias.append({
                "Código": item["codigo"],
                "Equipamento": item["descricao"],
                "Próxima calibração": item[
                    "data_proxima"
                ].strftime("%d/%m/%Y"),
                "Dias restantes": dias,
                "Status": item["status"]
            })


        st.dataframe(
            tabela_30_dias,
            use_container_width=True,
            hide_index=True
        )


    # ========================================================
    # CRONOGRAMA COMPLETO
    # ========================================================

    st.subheader("📊 Cronograma completo")

    if not registros_cronograma:

        st.info(
            "Ainda não existem calibrações cadastradas."
        )

    else:

        dados_tabela = []

        for item in registros_cronograma:

            dados_tabela.append({
                "Código": item["codigo"],
                "Equipamento": item["descricao"],
                "Localização": item["localizacao"] or "-",
                "Última calibração": (
                    item["data_calibracao"].strftime("%d/%m/%Y")
                    if item["data_calibracao"]
                    else "-"
                ),
                "Próxima calibração": (
                    item["data_proxima"].strftime("%d/%m/%Y")
                ),
                "Status": (
                    f"{obter_cor_status(item['status'])} "
                    f"{item['status']}"
                )
            })


        st.dataframe(
            dados_tabela,
            use_container_width=True,
            hide_index=True
        )