import streamlit as st

from database.db import conectar, criar_banco


criar_banco()


st.set_page_config(
    page_title="Sistema de Calibração",
    page_icon="🔧",
    layout="wide"
)


def buscar_equipamentos():
    conexao = conectar()

    equipamentos = conexao.execute("""
        SELECT
            id,
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
    periodicidade,
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
        periodicidade,
        status,
        observacoes
    ))

    conexao.commit()
    conexao.close()


st.title("🔧 Sistema de Gestão de Calibração")

st.write(
    "Controle de equipamentos, calibrações, "
    "pontos de medição, tolerâncias e histórico."
)

st.divider()


# ============================================================
# INDICADORES
# ============================================================

equipamentos = buscar_equipamentos()

col1, col2, col3 = st.columns(3)

with col1:
    st.metric(
        "Equipamentos cadastrados",
        len(equipamentos)
    )

with col2:
    st.metric(
        "Equipamentos ativos",
        sum(
            1
            for equipamento in equipamentos
            if equipamento["status"] == "Ativo"
        )
    )

with col3:
    st.metric(
        "Equipamentos inativos",
        sum(
            1
            for equipamento in equipamentos
            if equipamento["status"] == "Inativo"
        )
    )


st.divider()


# ============================================================
# CADASTRO
# ============================================================

st.subheader("Novo equipamento")


with st.form("form_equipamento"):

    col1, col2 = st.columns(2)

    with col1:

        codigo = st.text_input(
            "Código *",
            placeholder="Ex.: EQ-001"
        )

        descricao = st.text_input(
            "Descrição *",
            placeholder="Ex.: Paquímetro"
        )

        fabricante = st.text_input(
            "Fabricante",
            placeholder="Ex.: Mitutoyo"
        )

        modelo = st.text_input(
            "Modelo",
            placeholder="Ex.: 500-196-30"
        )

        numero_serie = st.text_input(
            "Número de série"
        )

    with col2:

        localizacao = st.text_input(
            "Localização",
            placeholder="Ex.: Laboratório"
        )

        responsavel = st.text_input(
            "Responsável"
        )

        periodicidade = st.number_input(
            "Periodicidade (meses)",
            min_value=1,
            max_value=120,
            value=12
        )

        status = st.selectbox(
            "Status",
            ["Ativo", "Inativo"]
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
                "O código do equipamento é obrigatório."
            )

        elif not descricao.strip():

            st.error(
                "A descrição do equipamento é obrigatória."
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
                    periodicidade,
                    status,
                    observacoes.strip()
                )

                st.success(
                    f"Equipamento {codigo} cadastrado com sucesso!"
                )

                st.rerun()

            except Exception as erro:

                if "UNIQUE constraint failed" in str(erro):

                    st.error(
                        f"O código {codigo} já está cadastrado."
                    )

                else:

                    st.error(
                        f"Erro ao cadastrar equipamento: {erro}"
                    )


st.divider()


# ============================================================
# LISTAGEM
# ============================================================

st.subheader("Equipamentos cadastrados")


if not equipamentos:

    st.info(
        "Nenhum equipamento cadastrado ainda."
    )

else:

    for equipamento in equipamentos:

        with st.expander(
            f'{equipamento["codigo"]} — {equipamento["descricao"]}'
        ):

            aba_detalhes, aba_editar = st.tabs(
                ["Detalhes", "Editar"]
            )

            # ==================================================
            # DETALHES
            # ==================================================

            with aba_detalhes:

                col1, col2 = st.columns(2)

                with col1:

                    st.write(
                        f'**Fabricante:** '
                        f'{equipamento["fabricante"] or "-"}'
                    )

                    st.write(
                        f'**Modelo:** '
                        f'{equipamento["modelo"] or "-"}'
                    )

                    st.write(
                        f'**Número de série:** '
                        f'{equipamento["numero_serie"] or "-"}'
                    )

                    st.write(
                        f'**Localização:** '
                        f'{equipamento["localizacao"] or "-"}'
                    )

                with col2:

                    st.write(
                        f'**Responsável:** '
                        f'{equipamento["responsavel"] or "-"}'
                    )

                    st.write(
                        f'**Periodicidade:** '
                        f'{equipamento["periodicidade_meses"]} meses'
                    )

                    st.write(
                        f'**Status:** '
                        f'{equipamento["status"]}'
                    )

                    st.write(
                        f'**Observações:** '
                        f'{equipamento["observacoes"] or "-"}'
                    )


            # ==================================================
            # EDITAR
            # ==================================================

            with aba_editar:

                with st.form(
                    f'form_editar_{equipamento["id"]}'
                ):

                    col1, col2 = st.columns(2)

                    with col1:

                        novo_codigo = st.text_input(
                            "Código *",
                            value=equipamento["codigo"]
                        )

                        nova_descricao = st.text_input(
                            "Descrição *",
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
                            max_value=120,
                            value=equipamento["periodicidade_meses"]
                        )

                        novo_status = st.selectbox(
                            "Status",
                            ["Ativo", "Inativo"],
                            index=(
                                0
                                if equipamento["status"] == "Ativo"
                                else 1
                            )
                        )

                        novas_observacoes = st.text_area(
                            "Observações",
                            value=equipamento["observacoes"] or ""
                        )

                    salvar = st.form_submit_button(
                        "Salvar alterações"
                    )


                    if salvar:

                        if not novo_codigo.strip():

                            st.error(
                                "O código do equipamento é obrigatório."
                            )

                        elif not nova_descricao.strip():

                            st.error(
                                "A descrição do equipamento é obrigatória."
                            )

                        else:

                            try:

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
                                    novo_codigo.strip(),
                                    nova_descricao.strip(),
                                    novo_fabricante.strip(),
                                    novo_modelo.strip(),
                                    novo_numero_serie.strip(),
                                    nova_localizacao.strip(),
                                    novo_responsavel.strip(),
                                    nova_periodicidade,
                                    novo_status,
                                    novas_observacoes.strip(),
                                    equipamento["id"]
                                ))

                                conexao.commit()
                                conexao.close()

                                st.success(
                                    "Equipamento atualizado com sucesso!"
                                )

                                st.rerun()

                            except Exception as erro:

                                if "UNIQUE constraint failed" in str(erro):

                                    st.error(
                                        f"O código {novo_codigo} já está cadastrado."
                                    )

                                else:

                                    st.error(
                                        f"Erro ao atualizar equipamento: {erro}"
                                    )


                st.divider()


                # ==================================================
                # EXCLUIR
                # ==================================================

                st.warning(
                    "A exclusão remove permanentemente este equipamento "
                    "do banco de dados."
                )

                if st.button(
                    "🗑️ Excluir equipamento",
                    key=f'excluir_{equipamento["id"]}'
                ):

                    conexao = conectar()

                    conexao.execute(
                        "DELETE FROM equipamentos WHERE id = ?",
                        (equipamento["id"],)
                    )

                    conexao.commit()
                    conexao.close()

                    st.success(
                        "Equipamento excluído com sucesso!"
                    )

                    st.rerun()