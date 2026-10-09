import sys
from pathlib import Path

# Adiciona a pasta principal do projeto ao caminho do Python
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.database.db import conectar, criar_banco


def main():
    criar_banco()
    conexao = conectar()

    print("=" * 60)
    print("LIMPEZA DOS DADOS DE TESTE")
    print("=" * 60)

    # IDs das calibrações criadas durante os testes
    ids_calibracoes_teste = (10, 11, 12, 13)

    placeholders = ",".join("?" for _ in ids_calibracoes_teste)

    calibracoes = conexao.execute(
        f"""
        SELECT
            c.id,
            c.equipamento_id,
            e.codigo,
            e.descricao,
            c.data_calibracao,
            c.laboratorio,
            c.certificado,
            c.resultado
        FROM calibracoes c
        INNER JOIN equipamentos e
            ON e.id = c.equipamento_id
        WHERE c.id IN ({placeholders})
        ORDER BY c.id
        """,
        ids_calibracoes_teste,
    ).fetchall()

    if not calibracoes:
        print("\nNenhuma das calibrações de teste foi encontrada.")
        conexao.close()
        return

    print("\nCalibrações encontradas:")

    for calibracao in calibracoes:
        print(
            f"ID: {calibracao['id']} | "
            f"Equipamento: {calibracao['codigo']} | "
            f"Descrição: {calibracao['descricao']} | "
            f"Data: {calibracao['data_calibracao']} | "
            f"Laboratório: {calibracao['laboratorio']} | "
            f"Certificado: {calibracao['certificado']} | "
            f"Resultado: {calibracao['resultado']}"
        )

    try:
        total_calibracoes = 0
        total_pontos = 0

        for calibracao in calibracoes:

            # Remove os pontos relacionados à calibração
            resultado = conexao.execute(
                """
                DELETE FROM pontos_calibracao
                WHERE calibracao_id = ?
                """,
                (calibracao["id"],),
            )

            total_pontos += resultado.rowcount

            # Remove somente a calibração de teste
            conexao.execute(
                """
                DELETE FROM calibracoes
                WHERE id = ?
                """,
                (calibracao["id"],),
            )

            total_calibracoes += 1

        conexao.commit()

        print("\nLimpeza concluída com sucesso.")
        print(f"Equipamentos removidos: 0")
        print(f"Calibrações removidas: {total_calibracoes}")
        print(f"Pontos de calibração removidos: {total_pontos}")

    except Exception as erro:
        conexao.rollback()

        print("\nERRO DURANTE A LIMPEZA.")
        print("Nenhuma alteração foi mantida no banco.")
        print(f"Erro: {erro}")

    finally:
        conexao.close()

    print("=" * 60)


if __name__ == "__main__":
    main()