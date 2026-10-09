from datetime import date

from dateutil.relativedelta import relativedelta

from app.database.db import conectar
from app.services.incertezas_referencia import (
    obter_incerteza_referencia,
    AVISO_HISTORICO,
)


def obter_equipamento(equipamento_id):
    conexao = conectar()

    try:
        return conexao.execute(
            """
            SELECT e.*
            FROM equipamentos e
            WHERE e.id = ?
            """,
            (equipamento_id,),
        ).fetchone()

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
              AND pp.ativo = 1
            ORDER BY pp.ordem, pp.id
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
):
    conexao = conectar()

    try:
        equipamento = conexao.execute(
            """
            SELECT
                id,
                codigo,
                plano_id,
                periodicidade_meses
            FROM equipamentos
            WHERE id = ?
              AND ativo = 1
            """,
            (equipamento_id,),
        ).fetchone()

        if equipamento is None:
            raise ValueError(
                "Equipamento não encontrado ou inativo."
            )

        codigo_equipamento = equipamento["codigo"]
        plano_id = equipamento["plano_id"]

        if plano_id is None:
            raise ValueError(
                "O equipamento não possui um plano de calibração."
            )

        pontos_plano = conexao.execute(
            """
            SELECT pp.*
            FROM pontos_plano pp
            WHERE pp.plano_id = ?
              AND pp.ativo = 1
            ORDER BY pp.ordem, pp.id
            """,
            (plano_id,),
        ).fetchall()

        if not pontos_plano:
            raise ValueError(
                "O plano de calibração não possui pontos cadastrados."
            )

        if isinstance(data_calibracao, str):
            data_calibracao_obj = date.fromisoformat(
                data_calibracao
            )
        else:
            data_calibracao_obj = data_calibracao

        periodicidade = equipamento["periodicidade_meses"]

        if periodicidade is None:
            raise ValueError(
                "Este equipamento não possui periodicidade "
                "de calibração cadastrada."
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
                observacoes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
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
            ),
        )

        calibracao_id = cursor.lastrowid

        for indice, ponto in enumerate(pontos_plano):
            incerteza_referencia, aviso = (
                obter_incerteza_referencia(
                    codigo_equipamento,
                    ponto,
                    indice,
                )
            )

            if incerteza_referencia is not None:
                # Converter para texto preserva também o zero:
                # o valor "0" não é confundido com campo vazio.
                incerteza = str(incerteza_referencia)
                observacao_ponto = aviso

            elif ponto["incerteza"] is not None:
                # Se não há correspondência no catálogo histórico,
                # preservar a incerteza que já estava no plano.
                incerteza = str(ponto["incerteza"])
                observacao_ponto = (
                    "Incerteza mantida do plano existente. "
                    "Confirmar unidade e validade metrológica. "
                    + (aviso or "")
                )

            else:
                incerteza = None
                observacao_ponto = (
                    aviso
                    or "Incerteza não localizada. "
                    "Consultar a planilha original."
                )

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
                    incerteza,
                    ponto["criterio"],
                    ponto["valor_minimo"],
                    ponto["valor_maximo"],
                    ponto["classe_exigida"],
                    "Pendente",
                    observacao_ponto,
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
            WHERE c.id = ?
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
            ORDER BY pc.ordem, pc.id
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

        if any(
            resultado == "Reprovado"
            for resultado in lista_resultados
        ):
            resultado_geral = "Reprovado"

        elif (
            lista_resultados
            and all(
                resultado == "Aprovado"
                for resultado in lista_resultados
            )
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


def atualizar_resultado_final_calibracao(
    calibracao_id,
    resultado_final,
):
    """Salva o parecer final escolhido pelo responsável."""
    conexao = conectar()

    try:
        conexao.execute(
            """
            UPDATE calibracoes
            SET
                resultado_final = ?,
                atualizado_em = CURRENT_TIMESTAMP
            WHERE id = ?
            """,
            (
                resultado_final,
                calibracao_id,
            ),
        )

        conexao.commit()

    except Exception:
        conexao.rollback()
        raise

    finally:
        conexao.close()