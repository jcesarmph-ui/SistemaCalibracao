"""Um nome só para o mesmo tipo ou local (pedido do usuário em 2026-11-10)."""

import sqlite3
from datetime import date

from calibracao.dados.repositorio import Instrumento, Repositorio
from calibracao.regras.padronizacao import (
    grafias_preferidas,
    locais,
    localizacao_padrao,
    preferidas_dos_locais,
    preferidas_dos_tipos,
    tipo_padrao,
)

HOJE = date(2026, 11, 10)


def test_grafia_da_maioria_e_empate_com_menos_maiusculas():
    assert grafias_preferidas(["Lâmina de Folga"] * 3 + ["Lâmina de folga"] * 4) == {
        "lamina de folga": "Lâmina de folga"}
    assert grafias_preferidas(["CT-01", "ct-01", "CT-01"])["ct-01"] == "CT-01"
    assert grafias_preferidas(["Lâmina de Folga", "Lâmina de folga"])["lamina de folga"] == \
        "Lâmina de folga"


def test_tipos_juntados_pelo_usuario():
    tipos = ["Paquímetro"] * 12 + ["Paquimetro analógico", "Balança",
                                   "Balança Suspensa - ULD-20000"]
    preferidas = preferidas_dos_tipos(tipos)
    assert tipo_padrao("Paquimetro analógico", preferidas) == "Paquímetro"
    assert tipo_padrao("Balança Suspensa - ULD-20000", preferidas) == "Balança"
    assert tipo_padrao("paquimetro", preferidas) == "Paquímetro"


def test_regua_para_furos_vira_regua_graduada():
    preferidas = preferidas_dos_tipos(["Régua graduada", "Régua graduada para furos"])
    assert tipo_padrao("Régua graduada para furos", preferidas) == "Régua graduada"
    assert tipo_padrao("régua GRADUADA para furos", {}) == "Régua graduada"
    assert tipo_padrao("Tipo novo", preferidas) == "Tipo novo"


def test_locais_separados_por_barra():
    assert locais("Serralheria / Manutenção") == ["Serralheria", "Manutenção"]
    assert locais("Serralheria/Manutenção - Orientação indicativa") == ["Serralheria",
                                                                        "Manutenção"]
    assert locais("Laboratório - Reserva") == ["Laboratório"]
    assert locais(None) == []


def test_localizacao_padrao_usa_o_nome_dos_outros_e_mantem_as_marcas():
    preferidas = preferidas_dos_locais(["Serralheria", "Manutenção", "CT-01"])
    assert localizacao_padrao("serralheria/manutenção", preferidas) == "Serralheria / Manutenção"
    assert localizacao_padrao("ct-01 - Orientação indicativa", preferidas) == \
        "CT-01 - Orientação indicativa"
    assert localizacao_padrao("CT-01 / ct-01", preferidas) == "CT-01"
    assert localizacao_padrao("CT - 1", preferidas) == "CT - 1"  # local novo fica como foi escrito


def test_salvar_usa_o_nome_que_ja_existe(tmp_path):
    repo = Repositorio.abrir(tmp_path / "calibracao.db", HOJE)
    repo.incluir_instrumento(Instrumento("LAF-001", "Lâmina de folga", localizacao="Serralheria"))
    repo.incluir_instrumento(Instrumento("MAN-001", "Manômetro", localizacao="Manutenção"))
    novo = repo.incluir_instrumento(Instrumento("LAF-002", "lâmina de Folga",
                                                localizacao="serralheria / MANUTENÇÃO"))
    salvo = repo.obter_instrumento(novo)
    assert (salvo.tipo, salvo.localizacao) == ("Lâmina de folga", "Serralheria / Manutenção")
    assert repo.locais_cadastrados() == ["Manutenção", "Serralheria"]
    repo.fechar()


def test_proximo_codigo_conta_todos_e_mantem_os_zeros(tmp_path):
    repo = Repositorio.abrir(tmp_path / "calibracao.db", HOJE)
    for codigo, tipo in [("PAQ-002", "Paquímetro"), ("PAQ-018", "Paquímetro"),
                         ("MA-09", "Máquina de arquear"), ("ESC-004", "Régua graduada"),
                         ("ESC-011", "Escala"), ("MN-004", "Manômetro"),
                         ("MAN-006", "Manômetro")]:
        repo.incluir_instrumento(Instrumento(codigo, tipo))
    lixo = repo.incluir_instrumento(Instrumento("PAQ-020", "Paquímetro"))
    assert repo.proximo_codigo("PAQ") == "PAQ-021"
    import datetime

    from calibracao.regras.lixeira import Tipo
    repo.enviar_para_lixeira(Tipo.INSTRUMENTO, lixo, None, datetime.datetime(2026, 11, 10))
    assert repo.proximo_codigo("paq") == "PAQ-021"  # o da Lixeira também conta
    assert repo.proximo_codigo("MA") == "MA-10"
    assert repo.proximo_codigo("ESC") == "ESC-012"  # Escala e Régua graduada juntas
    assert repo.proximo_codigo("XYZ") is None
    assert ("Manômetro", "MAN") in repo.siglas_dos_tipos()
    assert ("Manômetro", "MN") in repo.siglas_dos_tipos()
    repo.fechar()


def test_banco_antigo_e_acertado_uma_vez_ao_abrir(tmp_path):
    caminho = tmp_path / "calibracao.db"
    Repositorio.abrir(caminho, HOJE).fechar()
    conexao = sqlite3.connect(caminho)
    conexao.execute("DELETE FROM metadados WHERE chave = 'nomes_unificados'")  # banco de antes
    for codigo, tipo, local in [("LAF-1", "Lâmina de Folga", "CT-01"),
                                ("LAF-2", "Lâmina de folga", "ct-01"),
                                ("LAF-3", "Lâmina de folga", "CT-01"),
                                ("ESC-4", "Régua graduada para furos", "Serralheria/manutenção"),
                                ("MAN-1", "Manômetro", "Manutenção")]:
        conexao.execute("INSERT INTO instrumentos (codigo, tipo, localizacao) VALUES (?, ?, ?)",
                        (codigo, tipo, local))
    conexao.commit()
    conexao.close()
    repo = Repositorio.abrir(caminho, HOJE)
    dados = {i.codigo: (i.tipo, i.localizacao) for i in repo.listar_instrumentos()}
    assert dados["LAF-1"] == ("Lâmina de folga", "CT-01")
    assert dados["LAF-2"] == ("Lâmina de folga", "CT-01")
    assert dados["ESC-4"] == ("Régua graduada", "Serralheria / Manutenção")
    repo.fechar()
