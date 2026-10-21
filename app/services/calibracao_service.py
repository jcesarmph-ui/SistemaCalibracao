from datetime import date

from dateutil.relativedelta import relativedelta

from app.database.db import conectar


def _validar_edicao(conexao, calibracao_id):
    registro = conexao.execute(
        """SELECT 1 FROM calibracoes c JOIN equipamentos e ON e.id = c.equipamento_id
           WHERE c.id = ? AND c.excluido_em IS NULL AND e.excluido_em IS NULL""",
        (calibracao_id,),
    ).fetchone()
    if registro is None:
        raise ValueError("Calibração indisponível. Restaure a calibração e o equipamento antes de editar.")


def obter_equipamento(equipamento_id):
    conexao = conectar()

    try:
        equipamento = conexao.execute(
            """
            SELECT
                e.*
            FROM equipamentos e
            WHERE e.id = ? AND e.excluido_em IS NULL
            """,
            (equipamento_id,),
        ).fetchone()

        return equipamento

    finally:
        conexao.close()


def obter_pontos_plano(plano_id):
    conexao = conectar()

    try:
        return conexao.execute(
            """
            SELECT
                pp.id,
                pp.plano_id,
                pp.ordem,
                pp.ordem_original,
                pp.tipo_ponto,
                pp.descricao,
                pp.valor_nominal,
                pp.unidade,
                pp.tolerancia_inferior,
                pp.tolerancia_superior,
                pp.incerteza,
                pp.criterio,
                pp.valor_minimo,
                pp.valor_maximo,
                pp.classe_exigida,
                pp.ativo,
                NULL AS secao
            FROM pontos_plano pp
            WHERE pp.plano_id = ?
              AND pp.ativo = 1 AND pp.excluido_em IS NULL
              AND EXISTS (SELECT 1 FROM planos_calibracao p WHERE p.id = pp.plano_id AND p.excluido_em IS NULL)
            ORDER BY
                pp.ordem,
                pp.id
            """,
            (plano_id,),
        ).fetchall()

    finally:
        conexao.close()


def criar_calibracao(
    equipamento_id,
    data_calibracao,
    responsavel=None,
    laboratorio=None,
    certificado=None,
    observacoes=None,
    resultado_final=None,
    localizacao=None,
    custo_calibracao=None,
):
    conexao = conectar()

    try:
        equipamento = conexao.execute(
            """
            SELECT
                id,
                plano_id,
                periodicidade_meses
            FROM equipamentos
            WHERE id = ? AND excluido_em IS NULL
            """,
            (equipamento_id,),
        ).fetchone()

        if equipamento is None:
            raise ValueError("Equipamento não encontrado.")

        plano_id = equipamento["plano_id"]

        if plano_id is None:
            raise ValueError(
                "O equipamento não possui um plano de calibração."
            )

        pontos_plano = conexao.execute(
            """
            SELECT
                pp.*
            FROM pontos_plano pp
            WHERE pp.plano_id = ?
              AND pp.ativo = 1 AND pp.excluido_em IS NULL
              AND EXISTS (SELECT 1 FROM planos_calibracao p WHERE p.id = pp.plano_id AND p.excluido_em IS NULL)
            ORDER BY
                pp.ordem,
                pp.id
            """,
            (plano_id,),
        ).fetchall()

        if not pontos_plano:
            raise ValueError(
                "O plano de calibração não possui pontos cadastrados."
            )

        if isinstance(data_calibracao, str):
            data_calibracao_obj = date.fromisoformat(data_calibracao)
        else:
            data_calibracao_obj = data_calibracao

        periodicidade = equipamento["periodicidade_meses"]

        if periodicidade is None:
            raise ValueError(
                "Este equipamento não possui periodicidade de calibração cadastrada."
            )

        data_proxima = (
            data_calibracao_obj
            + relativedelta(months=int(periodicidade))
        )

        cursor = conexao.execute(
            """
            INSERT INTO calibracoes (
                equipamento_id,
                data_calibracao,
                data_proxima_calibracao,
                responsavel,
                laboratorio,
                certificado,
                resultado,
                resultado_final,
                observacoes,
                localizacao,
                custo_calibracao
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                equipamento_id,
                data_calibracao_obj.isoformat(),
                data_proxima.isoformat(),
                responsavel,
                laboratorio,
                certificado,
                "Pendente",
                resultado_final,
                observacoes,
                localizacao,
                custo_calibracao,
            ),
        )

        calibracao_id = cursor.lastrowid

        for ponto in pontos_plano:
            conexao.execute(
                """
                INSERT INTO pontos_calibracao (
                    calibracao_id,
                    ponto_plano_id,
                    ordem,
                    ordem_original,
                    tipo_ponto,
                    descricao,
                    valor_nominal,
                    valor_encontrado,
                    unidade,
                    tolerancia_inferior,
                    tolerancia_superior,
                    incerteza,
                    criterio,
                    valor_minimo,
                    valor_maximo,
                    classe_exigida,
                    resultado,
                    observacoes
                )
                VALUES (
                    ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    ?, ?, ?, ?, ?, ?
                )
                """,
                (
                    calibracao_id,
                    ponto["id"],
                    ponto["ordem"],
                    ponto["ordem_original"],
                    ponto["tipo_ponto"],
                    ponto["descricao"],
                    ponto["valor_nominal"],
                    None,
                    ponto["unidade"],
                    ponto["tolerancia_inferior"],
                    ponto["tolerancia_superior"],
                    ponto["incerteza"],
                    ponto["criterio"],
                    ponto["valor_minimo"],
                    ponto["valor_maximo"],
                    ponto["classe_exigida"],
                    "Pendente",
                    None,
                ),
            )

        conexao.execute(
            """
            UPDATE equipamentos
            SET
                data_ultima_calibracao = ?,
                data_proxima_calibracao = ?,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                data_calibracao_obj.isoformat(),
                data_proxima.isoformat(),
                equipamento_id,
            ),
        )

        conexao.commit()

        return calibracao_id

    except Exception:
        conexao.rollback()
        raise

    finally:
        conexao.close()


def obter_calibracao(calibracao_id):
    conexao = conectar()

    try:
        return conexao.execute(
            """
            SELECT
                c.*,
                e.codigo AS equipamento_codigo,
                e.descricao AS equipamento_nome
            FROM calibracoes c
            INNER JOIN equipamentos e
                ON e.id = c.equipamento_id
            WHERE c.id = ? AND c.excluido_em IS NULL AND e.excluido_em IS NULL
            """,
            (calibracao_id,),
        ).fetchone()

    finally:
        conexao.close()


def obter_pontos_calibracao(calibracao_id):
    conexao = conectar()

    try:
        return conexao.execute(
            """
            SELECT
                pc.id,
                pc.calibracao_id,
                pc.ponto_plano_id,
                pc.ordem,
                pc.ordem_original,
                pc.tipo_ponto,
                pc.descricao,
                pc.valor_nominal,
                pc.valor_encontrado,
                CASE
                    WHEN pc.valor_encontrado IS NOT NULL
                     AND pc.valor_nominal IS NOT NULL
                     AND UPPER(COALESCE(pc.tipo_ponto, 'NUMERICO')) NOT LIKE '%QUALITATIVO%'
                    THEN pc.valor_encontrado - pc.valor_nominal
                    ELSE NULL
                END AS desvio,
                pc.unidade,
                pc.tolerancia_inferior,
                pc.tolerancia_superior,
                pc.incerteza,
                pc.criterio,
                pc.valor_minimo,
                pc.valor_maximo,
                pc.classe_exigida,
                pc.resultado,
                pc.observacoes,
                NULL AS secao
            FROM pontos_calibracao pc
            WHERE pc.calibracao_id = ?
              AND EXISTS (SELECT 1 FROM calibracoes c JOIN equipamentos e ON e.id = c.equipamento_id
                          WHERE c.id = pc.calibracao_id AND c.excluido_em IS NULL AND e.excluido_em IS NULL)
            ORDER BY
                pc.ordem,
                pc.id
            """,
            (calibracao_id,),
        ).fetchall()

    finally:
        conexao.close()


def atualizar_ponto_calibracao(
    ponto_id,
    valor_encontrado,
    resultado,
    observacoes=None,
):
    conexao = conectar()

    try:
        conexao.execute(
            """
            UPDATE pontos_calibracao
            SET
                valor_encontrado = ?,
                resultado = ?,
                observacoes = ?
            WHERE id = ?
            """,
            (
                valor_encontrado,
                resultado,
                observacoes,
                ponto_id,
            ),
        )

        conexao.commit()

    except Exception:
        conexao.rollback()
        raise

    finally:
        conexao.close()


def salvar_pontos_calibracao(calibracao_id, pontos):
    conexao = conectar()

    try:
        _validar_edicao(conexao, calibracao_id)
        for ponto in pontos:
            conexao.execute(
                """
                UPDATE pontos_calibracao
                SET
                    valor_encontrado = ?,
                    resultado = ?,
                    observacoes = ?
                WHERE id = ?
                  AND calibracao_id = ?
                """,
                (
                    ponto.get("valor_encontrado"),
                    ponto.get("resultado"),
                    ponto.get("observacoes"),
                    ponto["id"],
                    calibracao_id,
                ),
            )

        resultados = conexao.execute(
            """
            SELECT resultado
            FROM pontos_calibracao
            WHERE calibracao_id = ?
            """,
            (calibracao_id,),
        ).fetchall()

        lista_resultados = [
            str(row["resultado"]).strip()
            for row in resultados
            if row["resultado"] is not None
            and str(row["resultado"]).strip()
        ]

        if any(resultado == "Reprovado" for resultado in lista_resultados):
            resultado_geral = "Reprovado"

        elif (
            lista_resultados
            and all(resultado == "Aprovado" for resultado in lista_resultados)
        ):
            resultado_geral = "Aprovado"

        elif lista_resultados:
            resultado_geral = "Aprovado com restrição"

        else:
            resultado_geral = "Pendente"

        conexao.execute(
            """
            UPDATE calibracoes
            SET
                resultado = ?,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                resultado_geral,
                calibracao_id,
            ),
        )

        conexao.commit()

        return resultado_geral

    except Exception:
        conexao.rollback()
        raise

    finally:
        conexao.close()


def atualizar_resultado_calibracao(
    calibracao_id,
    resultado,
):
    conexao = conectar()

    try:
        _validar_edicao(conexao, calibracao_id)
        conexao.execute(
            """
            UPDATE calibracoes
            SET
                resultado = ?,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                resultado,
                calibracao_id,
            ),
        )

        conexao.commit()

    except Exception:
        conexao.rollback()
        raise

    finally:
        conexao.close()

def atualizar_resultado_final_calibracao(calibracao_id, resultado_final):
    """Salva o parecer final escolhido pelo responsável pela calibração."""
    conexao = conectar()
    try:
        _validar_edicao(conexao, calibracao_id)
        conexao.execute(
            """
            UPDATE calibracoes
            SET resultado_final = ?, atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (resultado_final, calibracao_id),
        )
        conexao.commit()
    except Exception:
        conexao.rollback()
        raise
    finally:
        conexao.close()
