import sys
from pathlib import Path

# Adiciona a pasta principal do projeto ao caminho de importação do Python
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.database.db import conectar, criar_banco


def main():
    criar_banco()
    conexao = conectar()

    print("\n" + "=" * 60)
    print("VALIDAÇÃO DA IMPORTAÇÃO DOS DADOS REAIS")
    print("=" * 60)

    consultas = {
        "Tipos de instrumento": """
            SELECT COUNT(*) AS total
            FROM tipos_instrumento
        """,
        "Planos de calibração": """
            SELECT COUNT(*) AS total
            FROM planos_calibracao
        """,
        "Pontos dos planos": """
            SELECT COUNT(*) AS total
            FROM pontos_plano
        """,
        "Equipamentos": """
            SELECT COUNT(*) AS total
            FROM equipamentos
        """,
        "Calibrações": """
            SELECT COUNT(*) AS total
            FROM calibracoes
        """,
        "Pontos de calibração": """
            SELECT COUNT(*) AS total
            FROM pontos_calibracao
        """
    }

    for nome, sql in consultas.items():
        resultado = conexao.execute(sql).fetchone()
        print(f"{nome:<30}: {resultado['total']}")

    # ---------------------------------------------------------
    # EQUIPAMENTOS POR TIPO
    # ---------------------------------------------------------

    print("\n" + "-" * 60)
    print("EQUIPAMENTOS POR TIPO")
    print("-" * 60)

    consulta_tipos = """
        SELECT
            ti.nome AS tipo,
            COUNT(e.id) AS quantidade
        FROM equipamentos e
        LEFT JOIN tipos_instrumento ti
            ON ti.id = e.tipo_instrumento_id
        GROUP BY ti.nome
        ORDER BY ti.nome
    """

    resultados = conexao.execute(consulta_tipos).fetchall()

    total_equipamentos = 0

    for linha in resultados:
        tipo = linha["tipo"] if linha["tipo"] is not None else "SEM TIPO"

        print(
            f"{tipo:<35}: {linha['quantidade']}"
        )

        total_equipamentos += linha["quantidade"]

    print("-" * 60)
    print(f"{'TOTAL':<35}: {total_equipamentos}")

    # ---------------------------------------------------------
    # EQUIPAMENTOS SEM TIPO
    # ---------------------------------------------------------

    sem_tipo = conexao.execute("""
        SELECT
            id,
            codigo,
            descricao,
            tipo_instrumento_id,
            plano_id
        FROM equipamentos
        WHERE tipo_instrumento_id IS NULL
        ORDER BY codigo
    """).fetchall()

    print("\n" + "-" * 60)
    print("EQUIPAMENTOS SEM TIPO ASSOCIADO")
    print("-" * 60)

    if sem_tipo:
        print(f"Quantidade: {len(sem_tipo)}\n")

        for equipamento in sem_tipo:
            print(
                f"ID: {equipamento['id']} | "
                f"Código: {equipamento['codigo']} | "
                f"Descrição: {equipamento['descricao']} | "
                f"Plano ID: {equipamento['plano_id']}"
            )
    else:
        print("Nenhum equipamento sem tipo.")

    # ---------------------------------------------------------
    # EQUIPAMENTOS SEM PLANO
    # ---------------------------------------------------------

    sem_plano = conexao.execute("""
        SELECT
            id,
            codigo,
            descricao,
            tipo_instrumento_id,
            plano_id
        FROM equipamentos
        WHERE plano_id IS NULL
        ORDER BY codigo
    """).fetchall()

    print("\n" + "-" * 60)
    print("EQUIPAMENTOS SEM PLANO DE CALIBRAÇÃO")
    print("-" * 60)

    if sem_plano:
        print(f"Quantidade: {len(sem_plano)}\n")

        for equipamento in sem_plano:
            print(
                f"ID: {equipamento['id']} | "
                f"Código: {equipamento['codigo']} | "
                f"Descrição: {equipamento['descricao']} | "
                f"Tipo ID: {equipamento['tipo_instrumento_id']}"
            )
    else:
        print("Nenhum equipamento sem plano.")

    # ---------------------------------------------------------
    # PLANOS
    # ---------------------------------------------------------

    print("\n" + "-" * 60)
    print("PLANOS E QUANTIDADE DE PONTOS")
    print("-" * 60)

    consulta_planos = """
        SELECT
            p.id,
            ti.nome AS tipo,
            p.nome,
            p.faixa,
            p.resolucao,
            COUNT(pp.id) AS quantidade_pontos
        FROM planos_calibracao p
        LEFT JOIN tipos_instrumento ti
            ON ti.id = p.tipo_instrumento_id
        LEFT JOIN pontos_plano pp
            ON pp.plano_id = p.id
        GROUP BY
            p.id,
            ti.nome,
            p.nome,
            p.faixa,
            p.resolucao
        ORDER BY ti.nome, p.nome
    """

    planos = conexao.execute(consulta_planos).fetchall()

    for plano in planos:
        tipo = plano["tipo"] if plano["tipo"] is not None else "SEM TIPO"

        print(
            f"[{plano['id']:02d}] "
            f"{tipo} | "
            f"{plano['nome']} | "
            f"Faixa: {plano['faixa'] or '-'} | "
            f"Res.: {plano['resolucao'] or '-'} | "
            f"Pontos: {plano['quantidade_pontos']}"
        )

    # ---------------------------------------------------------
    # RESULTADO FINAL
    # ---------------------------------------------------------

    print("\n" + "=" * 60)

    if total_equipamentos == 173:
        print("OK: os 173 equipamentos foram importados.")
    else:
        print(
            f"ATENÇÃO: foram encontrados {total_equipamentos} equipamentos. "
            "O esperado é 173."
        )

    if sem_tipo:
        print(
            f"ATENÇÃO: {len(sem_tipo)} equipamento(s) estão sem tipo associado."
        )

    if sem_plano:
        print(
            f"ATENÇÃO: {len(sem_plano)} equipamento(s) estão sem plano associado."
        )

    print("=" * 60)

    conexao.close()


if __name__ == "__main__":
    main()