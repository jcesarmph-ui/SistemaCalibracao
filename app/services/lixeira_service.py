"""Exclusão reversível sem alterar snapshots, resultados ou incertezas."""
from datetime import datetime

from app.database.db import conectar

TIPOS = {
    "Equipamentos": ("equipamentos", "codigo || ' — ' || descricao"),
    "Calibrações": ("calibracoes", "'Calibração #' || id || ' — ' || data_calibracao || ' — ' || COALESCE(certificado, '')"),
    "Planos": ("planos_calibracao", "nome"),
    "Pontos dos planos": ("pontos_plano", "'Plano #' || plano_id || ' — ponto ' || ordem || ' — ' || COALESCE(descricao, '')"),
}


def _tabela(tipo):
    if tipo not in TIPOS:
        raise ValueError("Tipo de registro inválido.")
    return TIPOS[tipo][0]


def contadores():
    c = conectar()
    try:
        return {tipo: c.execute(f"SELECT COUNT(*) FROM {tabela} WHERE excluido_em IS NOT NULL").fetchone()[0]
                for tipo, (tabela, _) in TIPOS.items()}
    finally:
        c.close()


def listar(tipo=None, pesquisa="", limite=50, pagina=0):
    limite = min(max(int(limite), 1), 100)
    tipos = [tipo] if tipo else list(TIPOS)
    partes, parametros = [], []
    for categoria in tipos:
        tabela = _tabela(categoria)
        expressao = TIPOS[categoria][1]
        # O código do equipamento também pode localizar calibrações na lixeira.
        if categoria == "Calibrações":
            expressao += " || ' — ' || COALESCE((SELECT codigo || ' — ' || descricao FROM equipamentos WHERE id = equipamento_id), '')"
        partes.append(f"SELECT ? AS tipo, id, {expressao} AS registro, excluido_em, motivo_exclusao FROM {tabela} WHERE excluido_em IS NOT NULL")
        parametros.append(categoria)
    sql = "SELECT * FROM (" + " UNION ALL ".join(partes) + ") WHERE (registro LIKE ? OR CAST(id AS TEXT) LIKE ?)"
    termo = f"%{pesquisa.strip()}%"
    c = conectar()
    try:
        total = c.execute("SELECT COUNT(*) FROM (" + sql + ")", (*parametros, termo, termo)).fetchone()[0]
        linhas = c.execute(sql + " ORDER BY excluido_em DESC, tipo, id LIMIT ? OFFSET ?",
                           (*parametros, termo, termo, limite, max(int(pagina), 0) * limite)).fetchall()
        return linhas, total
    finally:
        c.close()


def detalhes(tipo, registro_id):
    tabela = _tabela(tipo)
    c = conectar()
    try:
        r = c.execute(f"SELECT * FROM {tabela} WHERE id = ? AND excluido_em IS NOT NULL", (registro_id,)).fetchone()
        return dict(r) if r else None
    finally:
        c.close()


def _dependencias_restauracao(c, tipo, registro):
    pais = []
    if tipo in ("Equipamentos", "Pontos dos planos"):
        pais = [("planos_calibracao", registro["plano_id"], "plano")]
    elif tipo == "Calibrações":
        pais = [("equipamentos", registro["equipamento_id"], "equipamento")]
    for tabela, id_pai, nome in pais:
        if id_pai is not None:
            pai = c.execute(f"SELECT excluido_em FROM {tabela} WHERE id = ?", (id_pai,)).fetchone()
            if pai is None or pai["excluido_em"] is not None:
                raise ValueError(f"Restaure primeiro o {nome} associado.")


def impedimento_permanente(c, tipo, registro_id):
    if tipo == "Calibrações":
        return "A exclusão permanente de calibrações está bloqueada para proteger o histórico."
    dependencias = {
        "Equipamentos": [("calibracoes", "equipamento_id")],
        "Planos": [("equipamentos", "plano_id"), ("pontos_plano", "plano_id")],
        "Pontos dos planos": [("pontos_calibracao", "ponto_plano_id")],
    }[tipo]
    for tabela, coluna in dependencias:
        if c.execute(f"SELECT 1 FROM {tabela} WHERE {coluna} = ? LIMIT 1", (registro_id,)).fetchone():
            return "Operação bloqueada por dependências existentes, inclusive registros na lixeira."
    return None


def alterar(tipo, registro_id, acao, motivo=None, confirmacao=None):
    tabela = _tabela(tipo)
    c = conectar()
    try:
        c.execute("BEGIN IMMEDIATE")
        registro = c.execute(f"SELECT * FROM {tabela} WHERE id = ?", (registro_id,)).fetchone()
        if registro is None:
            raise ValueError("Registro não encontrado.")
        if acao == "excluir":
            if registro["excluido_em"] is not None:
                raise ValueError("O registro já está na lixeira.")
            c.execute(f"UPDATE {tabela} SET excluido_em = ?, motivo_exclusao = ? WHERE id = ?",
                      (datetime.now().astimezone().isoformat(timespec="seconds"), (motivo or "").strip() or None, registro_id))
        elif acao in ("restaurar", "permanente"):
            if registro["excluido_em"] is None:
                raise ValueError("O registro precisa estar na lixeira.")
            if acao == "restaurar":
                _dependencias_restauracao(c, tipo, registro)
                c.execute(f"UPDATE {tabela} SET excluido_em = NULL, motivo_exclusao = NULL WHERE id = ?", (registro_id,))
            else:
                if confirmacao != "EXCLUIR":
                    raise ValueError("Digite EXCLUIR para confirmar a exclusão permanente.")
                bloqueio = impedimento_permanente(c, tipo, registro_id)
                if bloqueio:
                    raise ValueError(bloqueio)
                c.execute(f"DELETE FROM {tabela} WHERE id = ?", (registro_id,))
        else:
            raise ValueError("Operação inválida.")
        c.commit()
    except Exception:
        c.rollback()
        raise
    finally:
        c.close()
