"""Estilos de status e operações de lixeira compartilhados pela interface."""
import pandas as pd
import streamlit as st

from app.services import lixeira_service as lixeira

CORES = {
    "regular": "background-color: #dcfce7; color: #14532d; font-weight: 600",
    "alerta": "background-color: #fef3c7; color: #78350f; font-weight: 600",
    "erro": "background-color: #fee2e2; color: #991b1b; font-weight: 600",
    "neutro": "background-color: #e5e7eb; color: #374151",
}


def estilo_status(valor):
    texto = str(valor).strip().upper()
    if texto in ("APROVADO", "FEITO", "EM DIA", "PROGRAMADAS", "REGULAR", "ATIVO"):
        return CORES["regular"]
    if texto.startswith("REPROVADO") or texto in ("VENCIDA", "VENCIDAS"):
        return CORES["erro"]
    if texto in ("PENDENTE", "APROVADO COM RESTRIÇÃO", "PRÓXIMAS (30 DIAS)"):
        return CORES["alerta"]
    return CORES["neutro"]


def tabela_status(df):
    colunas = [c for c in ("Resultado", "Status", "Situação") if c in df.columns]
    return df.style.map(estilo_status, subset=colunas) if colunas else df


def sucesso(mensagem):
    st.session_state["mensagem_operacao"] = mensagem
    st.rerun()


def botao_lixeira(tipo, registro_id, nome):
    chave = f"lixeira_{tipo}_{registro_id}"
    if st.button("Enviar para a lixeira", key=chave, icon=":material/delete:"):
        st.session_state["confirmacao_lixeira"] = chave
    if st.session_state.get("confirmacao_lixeira") == chave:
        st.warning(f"Enviar para a lixeira — {tipo}: {nome} (ID {registro_id})? Os dados e vínculos serão preservados.")
        motivo = st.text_input("Motivo da exclusão (opcional)", key=chave + "_motivo")
        c1, c2 = st.columns(2)
        if c1.button("Confirmar envio à lixeira", key=chave + "_confirmar", type="primary"):
            try:
                lixeira.alterar(tipo, registro_id, "excluir", motivo=motivo)
                st.session_state.pop("confirmacao_lixeira", None)
                sucesso("Registro enviado para a lixeira.")
            except Exception as erro:
                st.error(str(erro))
        if c2.button("Cancelar", key=chave + "_cancelar"):
            st.session_state.pop("confirmacao_lixeira", None)
            st.rerun()


def pagina_lixeira():
    st.subheader("Lixeira")
    st.caption("A restauração mantém os dados originais. Registros inativos continuam inativos ao restaurar.")
    contagens = lixeira.contadores()
    for coluna, (tipo, total) in zip(st.columns(4), contagens.items()):
        coluna.metric(tipo, total)
    tipo = st.selectbox("Tipo de registro", ["Todos", *lixeira.TIPOS], key="lixeira_tipo")
    pesquisa = st.text_input("Pesquisar por código ou descrição", key="lixeira_busca")
    pagina = int(st.number_input("Página", min_value=1, value=1, step=1, key="lixeira_pagina"))
    linhas, total = lixeira.listar(None if tipo == "Todos" else tipo, pesquisa, pagina=pagina - 1)
    st.caption(f"{total} registro(s) encontrado(s) · até 50 por página")
    if not linhas:
        st.info("Nenhum registro nesta página. Ajuste os filtros ou a página.")
        return
    st.dataframe(pd.DataFrame([dict(r) for r in linhas]).rename(columns={
        "tipo": "Tipo", "id": "ID", "registro": "Registro", "excluido_em": "Data da exclusão", "motivo_exclusao": "Motivo"}), hide_index=True, width="stretch")
    opcoes = {f"{r['tipo']} · {r['registro']} (ID {r['id']})": r for r in linhas}
    selecionado = st.selectbox("Registro para restaurar ou excluir permanentemente", list(opcoes), key="lixeira_registro")
    r = opcoes[selecionado]
    with st.expander("Visualizar dados originais do registro"):
        dados = lixeira.detalhes(r["tipo"], r["id"])
        if dados:
            st.dataframe(pd.DataFrame({"Campo": list(dados), "Valor": [str(v) if v is not None else "Não informado" for v in dados.values()]}), hide_index=True)
    chave = f"permanente_{r['tipo']}_{r['id']}"
    c1, c2 = st.columns(2)
    if c1.button("Restaurar", icon=":material/restore:", key="lixeira_restaurar", type="primary"):
        try:
            lixeira.alterar(r["tipo"], r["id"], "restaurar")
            sucesso("Registro restaurado.")
        except Exception as erro:
            st.error(str(erro))
    if c2.button("Excluir permanentemente", icon=":material/delete_forever:", key="lixeira_permanente"):
        st.session_state["confirmacao_permanente"] = chave
    if st.session_state.get("confirmacao_permanente") == chave:
        st.error(f"Excluir permanentemente: {selecionado}. Esta operação não poderá ser desfeita pela lixeira.")
        c = lixeira.conectar()
        try:
            bloqueio = lixeira.impedimento_permanente(c, r["tipo"], r["id"])
        finally:
            c.close()
        if bloqueio:
            st.warning(bloqueio)
        confirmacao = st.text_input("Digite EXCLUIR para confirmar", key=chave + "_texto")
        confirmar, cancelar = st.columns(2)
        if confirmar.button("Confirmar exclusão permanente", key=chave + "_confirmar", type="primary", disabled=bool(bloqueio) or confirmacao != "EXCLUIR"):
            try:
                lixeira.alterar(r["tipo"], r["id"], "permanente", confirmacao=confirmacao)
                st.session_state.pop("confirmacao_permanente", None)
                sucesso("Exclusão permanente concluída.")
            except Exception as erro:
                st.error(str(erro))
        if cancelar.button("Cancelar exclusão permanente", key=chave + "_cancelar"):
            st.session_state.pop("confirmacao_permanente", None)
            st.rerun()
