from app.database.db import conectar

conexao = conectar()

conexao.execute("""
    UPDATE equipamentos
    SET
        data_ultima_calibracao = NULL,
        data_proxima_calibracao = NULL
    WHERE codigo IN ('PAQ-004', 'MAN-005')
""")

conexao.commit()

print("OK - datas removidas de PAQ-004 e MAN-005.")

conexao.close()