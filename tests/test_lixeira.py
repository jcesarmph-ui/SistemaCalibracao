import ast
from contextlib import closing
import sqlite3
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from app.database import db
from app.services import lixeira_service as lixo
from app.services import calibracao_service as calibracao
from app.interface import estilo_status, CORES

RAIZ = Path(__file__).resolve().parents[1]
ORIGINAL = RAIZ / "data" / "calibracao.db"


class LixeiraTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory(dir=RAIZ / "tests")
        self.pasta = Path(self.temp.name)
        self.copia = self.pasta / "calibracao.db"
        with closing(sqlite3.connect(f"file:{ORIGINAL.as_posix()}?mode=ro", uri=True)) as origem, closing(sqlite3.connect(self.copia)) as destino:
            origem.backup(destino)
        self.patch_path = patch.object(db, "DB_PATH", self.copia)
        self.patch_data = patch.object(db, "DATA_DIR", self.pasta)
        self.patch_path.start()
        self.patch_data.start()
        db.criar_banco()

    def tearDown(self):
        self.patch_data.stop()
        self.patch_path.stop()
        self.temp.cleanup()

    def sql(self, sql, valores=()):
        c = db.conectar()
        try:
            cursor = c.execute(sql, valores)
            linhas = cursor.fetchall()
            id_novo = cursor.lastrowid
            c.commit()
            return linhas if linhas else id_novo
        finally:
            c.close()

    def novo(self):
        tipo = self.sql("INSERT INTO tipos_instrumento(nome) VALUES ('Tipo de teste da lixeira')")
        plano = self.sql("INSERT INTO planos_calibracao(nome, ativo, tipo_instrumento_id) VALUES ('Plano de teste', 1, ?)", (tipo,))
        ponto = self.sql("INSERT INTO pontos_plano(plano_id, ordem, descricao, valor_nominal, incerteza) VALUES (?, 1, 'Ponto de teste', 10, '0,123')", (plano,))
        eq = self.sql("INSERT INTO equipamentos(codigo, descricao, plano_id, periodicidade_meses, tipo_instrumento_id) VALUES ('TEST-LIXEIRA', 'Equipamento de teste', ?, 12, ?)", (plano, tipo))
        return plano, ponto, eq

    def test_migracao_preserva_todos_campos_e_idempotente(self):
        with closing(sqlite3.connect(f"file:{ORIGINAL.as_posix()}?mode=ro", uri=True)) as origem, closing(sqlite3.connect(self.copia)) as destino:
            for (tabela,) in origem.execute("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"):
                campos = [r[1] for r in origem.execute(f'PRAGMA table_info({tabela})')]
                selecao = ', '.join(f'"{c}"' for c in campos)
                self.assertEqual(origem.execute(f'SELECT {selecao} FROM {tabela} ORDER BY id').fetchall(), destino.execute(f'SELECT {selecao} FROM {tabela} ORDER BY id').fetchall())
        db.criar_banco()
        c = db.conectar()
        try:
            self.assertEqual(c.execute('PRAGMA integrity_check').fetchone()[0], 'ok')
            self.assertEqual(c.execute('PRAGMA foreign_key_check').fetchall(), [])
        finally:
            c.close()

    def test_equipamento_restauracao_preserva_inatividade(self):
        _, _, eq = self.novo()
        self.sql('UPDATE equipamentos SET ativo=0 WHERE id=?', (eq,))
        lixo.alterar('Equipamentos', eq, 'excluir', motivo='Teste')
        r = self.sql('SELECT * FROM equipamentos WHERE id=?', (eq,))[0]
        self.assertIsNotNone(r['excluido_em'])
        self.assertEqual(r['motivo_exclusao'], 'Teste')
        lixo.alterar('Equipamentos', eq, 'restaurar')
        self.assertEqual(self.sql('SELECT ativo FROM equipamentos WHERE id=?', (eq,))[0][0], 0)

    def test_calibracao_pontos_e_incertezas_preservados(self):
        plano, ponto, eq = self.novo()
        cal = calibracao.criar_calibracao(eq, '2026-01-31')
        antes = [tuple(r) for r in calibracao.obter_pontos_calibracao(cal)]
        self.sql("UPDATE pontos_plano SET incerteza='99' WHERE id=?", (ponto,))
        lixo.alterar('Calibrações', cal, 'excluir')
        self.assertIsNone(calibracao.obter_calibracao(cal))
        self.assertEqual(calibracao.obter_pontos_calibracao(cal), [])
        lixo.alterar('Calibrações', cal, 'restaurar')
        self.assertEqual(antes, [tuple(r) for r in calibracao.obter_pontos_calibracao(cal)])
        lixo.alterar('Pontos dos planos', ponto, 'excluir')
        self.assertEqual(calibracao.obter_pontos_plano(plano), [])
        self.assertEqual(antes, [tuple(r) for r in calibracao.obter_pontos_calibracao(cal)])
        lixo.alterar('Pontos dos planos', ponto, 'restaurar')
        self.assertEqual(len(calibracao.obter_pontos_plano(plano)), 1)

    def test_dependencias_restauracao_e_criacao(self):
        plano, ponto, eq = self.novo()
        cal = calibracao.criar_calibracao(eq, '2026-01-01')
        lixo.alterar('Pontos dos planos', ponto, 'excluir')
        lixo.alterar('Equipamentos', eq, 'excluir')
        lixo.alterar('Calibrações', cal, 'excluir')
        lixo.alterar('Planos', plano, 'excluir')
        for tipo, id_ in [('Pontos dos planos', ponto), ('Equipamentos', eq), ('Calibrações', cal)]:
            with self.assertRaisesRegex(ValueError, 'Restaure primeiro'):
                lixo.alterar(tipo, id_, 'restaurar')
        with self.assertRaises(ValueError):
            calibracao.criar_calibracao(eq, '2026-01-01')
        lixo.alterar('Planos', plano, 'restaurar')
        lixo.alterar('Pontos dos planos', ponto, 'restaurar')
        lixo.alterar('Equipamentos', eq, 'restaurar')
        lixo.alterar('Calibrações', cal, 'restaurar')
        self.assertIsNotNone(calibracao.obter_calibracao(cal))

    def test_exclusoes_permanentes_protegidas(self):
        plano, ponto, eq = self.novo()
        cal = calibracao.criar_calibracao(eq, '2026-01-01')
        for tipo, id_ in [('Equipamentos', eq), ('Planos', plano), ('Pontos dos planos', ponto), ('Calibrações', cal)]:
            lixo.alterar(tipo, id_, 'excluir')
            with self.assertRaises(ValueError):
                lixo.alterar(tipo, id_, 'permanente', confirmacao='EXCLUIR')
        self.assertEqual(self.sql('PRAGMA foreign_key_check'), 0)

    def test_exclusao_permitida_confirmacao_filtros_reinicio(self):
        plano, ponto, eq = self.novo()
        for tipo, id_ in [('Equipamentos', eq), ('Pontos dos planos', ponto), ('Planos', plano)]:
            lixo.alterar(tipo, id_, 'excluir')
            with self.assertRaises(ValueError):
                lixo.alterar(tipo, id_, 'permanente', confirmacao='excluir')
            self.assertEqual(len(lixo.listar(tipo, str(id_))[0]), 1)
            db.criar_banco()
            self.assertGreater(lixo.contadores()[tipo], 0)
            lixo.alterar(tipo, id_, 'permanente', confirmacao='EXCLUIR')
            self.assertEqual(lixo.listar(tipo, str(id_))[1], 0)

    def test_estilos_e_calculo_sem_incerteza(self):
        self.assertEqual(estilo_status('APROVADO'), CORES['regular'])
        self.assertEqual(estilo_status('Reprovado'), CORES['erro'])
        self.assertEqual(estilo_status('Próximas (30 dias)'), CORES['alerta'])
        tree = ast.parse((RAIZ / 'main.py').read_text(encoding='utf-8'))
        funcs = [n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name in ('_numero_incerteza', 'desvio_final_com_incerteza', 'calcular_resultado_ponto')]
        contexto = {}
        exec(compile(ast.Module(body=funcs, type_ignores=[]), 'main.py', 'exec'), contexto)
        ponto = dict(valor_nominal=10, valor_minimo=None, valor_maximo=None, tolerancia_inferior=-1, tolerancia_superior=1, incerteza='0,123')
        self.assertEqual(contexto['calcular_resultado_ponto'](ponto, 10), 'Aprovado')
        self.assertEqual(contexto['calcular_resultado_ponto'](ponto, 11), 'Reprovado')
        ponto['incerteza'] = None
        self.assertIn('incerteza ausente', contexto['calcular_resultado_ponto'](ponto, 10))
        self.assertIsNone(contexto['desvio_final_com_incerteza'](10, 10, None))

    def test_interface_cancelar_excluir_restaurar_e_filtros(self):
        from streamlit.testing.v1 import AppTest
        plano, ponto, eq = self.novo()
        lixo.alterar('Equipamentos', eq, 'excluir')
        at = AppTest.from_file(str(RAIZ / 'main.py'), default_timeout=30).run()
        self.assertEqual(len(at.exception), 0, str(at.exception))
        at.selectbox(key='lixeira_tipo').select('Equipamentos').run()
        at.text_input(key='lixeira_busca').set_value('TEST-LIXEIRA').run()
        self.assertEqual(len(at.exception), 0, str(at.exception))
        at.button(key='lixeira_permanente').click().run()
        self.assertTrue(at.button(key=f'permanente_Equipamentos_{eq}_confirmar').disabled)
        at.text_input(key=f'permanente_Equipamentos_{eq}_texto').set_value('EXCLUIR').run()
        at.button(key=f'permanente_Equipamentos_{eq}_cancelar').click().run()
        self.assertEqual(lixo.listar('Equipamentos', 'TEST-LIXEIRA')[1], 1)
        at.button(key='lixeira_restaurar').click().run()
        self.assertEqual(lixo.listar('Equipamentos', 'TEST-LIXEIRA')[1], 0)
        self.assertTrue(any(s.value == 'Registro restaurado.' for s in at.success))
        # Exclusão lógica pela tela operacional e cancelamento.
        seletor = next(s for s in at.selectbox if s.label == 'Selecione o equipamento')
        seletor.select(next(o for o in seletor.options if 'TEST-LIXEIRA' in o)).run()
        chave = f'lixeira_Equipamentos_{eq}'
        at.button(key=chave).click().run()
        at.button(key=chave + '_cancelar').click().run()
        self.assertEqual(lixo.listar('Equipamentos', 'TEST-LIXEIRA')[1], 0)
        at.button(key=chave).click().run()
        at.text_input(key=chave + '_motivo').set_value('Teste de interface').run()
        at.button(key=chave + '_confirmar').click().run()
        self.assertEqual(lixo.listar('Equipamentos', 'TEST-LIXEIRA')[0][0]['motivo_exclusao'], 'Teste de interface')
        at.button(key='lixeira_permanente').click().run()
        at.text_input(key=f'permanente_Equipamentos_{eq}_texto').set_value('EXCLUIR').run()
        at.button(key=f'permanente_Equipamentos_{eq}_confirmar').click().run()
        self.assertEqual(lixo.listar('Equipamentos', 'TEST-LIXEIRA')[1], 0)
        self.assertEqual(len(at.exception), 0, str(at.exception))
        reiniciado = AppTest.from_file(str(RAIZ / 'main.py'), default_timeout=30).run()
        self.assertEqual(len(reiniciado.exception), 0, str(reiniciado.exception))

    def test_interface_resultados_cronograma_e_plano_excluido(self):
        from streamlit.testing.v1 import AppTest
        plano, ponto, eq = self.novo()
        self.sql("INSERT INTO pontos_plano(plano_id, ordem, descricao, valor_nominal, incerteza) VALUES (?, 2, 'Segundo ponto', 10, '0,25')", (plano,))
        cal = calibracao.criar_calibracao(eq, '2025-01-01')
        pontos = calibracao.obter_pontos_calibracao(cal)
        calibracao.salvar_pontos_calibracao(cal, [
            dict(id=pontos[0]['id'], valor_encontrado=10, resultado='Aprovado'),
            dict(id=pontos[1]['id'], valor_encontrado=12, resultado='Reprovado'),
        ])
        at = AppTest.from_file(str(RAIZ / 'main.py'), default_timeout=30).run()
        seletor = next(s for s in at.selectbox if s.label == 'Selecione o equipamento')
        seletor.select(next(o for o in seletor.options if 'TEST-LIXEIRA' in o)).run()
        self.assertEqual(len(at.exception), 0, str(at.exception))
        tabela = next(d for d in at.dataframe if 'Resultado' in d.value.columns)
        self.assertIn('#14532d', tabela.proto.arrow_data.styler.styles)
        self.assertIn('#991b1b', tabela.proto.arrow_data.styler.styles)
        at.selectbox(key='cronograma_filtro_status_atual').select('Vencidas').run()
        self.assertEqual(len(at.exception), 0, str(at.exception))
        at.button(key=f'gerar_grafico_{eq}').click().run()
        self.assertEqual(len(at.exception), 0, str(at.exception))
        lixo.alterar('Planos', plano, 'excluir')
        at.run()
        self.assertEqual(len(at.exception), 0, str(at.exception))
        self.assertTrue(any('plano associado' in w.value for w in at.warning))


if __name__ == '__main__':
    unittest.main()
