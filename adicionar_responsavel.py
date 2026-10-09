from app.database.db import conectar

conexao = conectar()

try:
    conexao.execute("""
        ALTER TABLE calibracoes
        ADD COLUMN responsavel TEXT
    """)

    conexao.commit()

    print("OK - coluna responsavel adicionada à tabela calibracoes.")

except Exception as erro:
    conexao.rollback()
    print(f"ERRO: {erro}")

finally:
    conexao.close()