"""Melhorias do cadastro de instrumento da versão 1.2.0 (pedidos do usuário em 2026-11-10)."""

import os
from datetime import date

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import QDate  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from calibracao.dados.repositorio import Instrumento, Repositorio  # noqa: E402
from calibracao.interface.componentes import (  # noqa: E402
    data_livre_para_banco,
    data_livre_para_tela,
)
from calibracao.interface.janela import JanelaPrincipal  # noqa: E402

HOJE = date(2026, 11, 10)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def janela(app, tmp_path):
    repo = Repositorio.abrir(tmp_path / "calibracao.db", HOJE)
    for codigo, tipo, local in [("PAQ-017", "Paquímetro", "CT-01"),
                                ("PAQ-018", "Paquímetro", "Serralheria / Manutenção"),
                                ("TRE-009", "Trena", "Manutenção")]:
        repo.incluir_instrumento(Instrumento(codigo, tipo, localizacao=local,
                                             data_compra="2023-11-16"))
    tela = JanelaPrincipal(repo, tmp_path, HOJE)
    yield tela
    tela.close()
    repo.fechar()


def test_data_de_compra_aparece_dd_mm_aaaa_e_texto_livre_fica_igual():
    assert data_livre_para_tela("2023-11-16") == "16/11/2023"
    assert data_livre_para_tela("Transferida para Filial 1") == "Transferida para Filial 1"
    assert data_livre_para_tela(None) == ""
    assert data_livre_para_banco("16/11/2023") == "2023-11-16"
    assert data_livre_para_banco(" - ") == "-"
    assert data_livre_para_banco("") is None


def test_calendario_da_data_de_compra(janela):
    aba = janela.aba_instrumentos
    edicao = aba.criar_janela_edicao(aba.repo.listar_instrumentos()[0])
    assert edicao.campos["data_compra"].text() == "16/11/2023"
    assert not edicao.tem_alteracao()  # só mostrar em dd/mm/aaaa não é alteração
    edicao.calendario_compra.abrir()
    assert edicao.calendario_compra.calendario.selectedDate() == QDate(2023, 11, 16)
    edicao.calendario_compra._escolheu(QDate(2024, 2, 5))
    assert edicao.campos["data_compra"].text() == "05/02/2024"
    edicao.salvar_instrumento()
    salvo = aba.repo.obter_instrumento(edicao.instrumento.id)
    assert salvo.data_compra == "2024-02-05"
    assert aba.valores["data_compra"].text() == "<b>05/02/2024</b>"


def test_filtro_mostra_o_instrumento_em_cada_local(janela):
    aba = janela.aba_instrumentos
    opcoes = [aba.filtro_local.itemText(i) for i in range(aba.filtro_local.count())]
    assert "Serralheria / Manutenção" not in opcoes
    assert {"Serralheria", "Manutenção", "CT-01"} <= set(opcoes)
    aba.filtro_local.setCurrentText("Manutenção")
    assert {aba.tabela.item(n, 0).text() for n in range(aba.tabela.rowCount())} == {
        "PAQ-018", "TRE-009"}
    aba.filtro_local.setCurrentText("Serralheria")
    assert [aba.tabela.item(n, 0).text() for n in range(aba.tabela.rowCount())] == ["PAQ-018"]


def test_titulo_com_dq05(janela):
    titulos = [r.text() for r in janela.findChildren(type(janela.faixa_teste))
               if r.objectName() == "titulo"]
    assert titulos == ["DQ-05 CALIBRAÇÃO DE INSTRUMENTOS"]


def novo_cadastro(janela):
    return janela.aba_instrumentos.criar_janela_edicao(None)


def test_lista_de_tipos_no_codigo_preenche_o_proximo_numero(janela):
    edicao = novo_cadastro(janela)
    itens = [edicao.lista_codigo.itemText(i) for i in range(edicao.lista_codigo.count())]
    assert itens == ["Paquímetro (PAQ)", "Trena (TRE)"]
    assert edicao.campos["codigo"].text() == ""  # a lista não escreve nada sozinha
    edicao.escolher_sigla(0)
    assert edicao.campos["codigo"].text() == "PAQ-019"
    assert edicao.campos["tipo"].text() == "Paquímetro"


def test_digitar_a_sigla_sugere_e_enter_completa(janela):
    edicao = novo_cadastro(janela)
    edicao.campos["codigo"].setText("paq-")
    assert "PAQ-019" in edicao.dica_codigo.text() and "Enter" in edicao.dica_codigo.text()
    edicao.usar_proximo_codigo()
    assert edicao.campos["codigo"].text() == "PAQ-019"
    assert "próximo número livre" in edicao.dica_codigo.text()
    edicao.campos["codigo"].setText("PAQ-030")  # outro número: é escolha do usuário
    assert edicao.dica_codigo.text() == ""
    edicao.usar_proximo_codigo()
    assert edicao.campos["codigo"].text() == "PAQ-030"
    edicao.campos["codigo"].setText("PAQ-018")
    assert "Já existe" in edicao.dica_codigo.text()


def test_tipo_e_local_com_sugestoes_sem_ligar_para_acento(janela):
    edicao = novo_cadastro(janela)
    tipo = edicao.campos["tipo"]
    tipo.setText("paqui")
    assert tipo.filtradas() == ["Paquímetro"]
    tipo.escolher("Paquímetro")
    assert tipo.text() == "Paquímetro" and edicao.aviso_tipo.text() == ""
    local = edicao.campos["localizacao"]
    local.setText("serra")
    assert local.filtradas() == ["Serralheria"]
    local.escolher("Serralheria")
    local.mais_um()
    assert local.text() == "Serralheria / "
    local.setText("Serralheria / manu")
    assert local.filtradas() == ["Manutenção"]
    local.escolher("Manutenção")
    assert local.text() == "Serralheria / Manutenção"
    assert edicao.aviso_local.text() == ""


def test_nome_novo_avisa_parecidos_e_pergunta_ao_salvar(janela, nome_novo_confirmado):
    perguntas, respostas = nome_novo_confirmado
    edicao = novo_cadastro(janela)
    edicao.campos["codigo"].setText("PAQ-019")
    edicao.campos["tipo"].setText("Paquímetro")
    edicao.campos["localizacao"].setText("CT - 1")
    assert "local novo" in edicao.aviso_local.text()
    assert "Parece com: CT-01" in edicao.aviso_local.text()
    respostas.append(False)  # "Voltar e escolher da lista"
    edicao.salvar_instrumento()
    assert perguntas == [['local "CT - 1"']]
    assert not edicao.result()  # não salvou
    assert all(i.codigo != "PAQ-019" for i in janela.repo.listar_instrumentos())
    edicao.campos["localizacao"].setText("Almoxarifado")  # local realmente novo
    edicao.salvar_instrumento()  # responde "Criar novo"
    assert edicao.result()
    salvo = next(i for i in janela.repo.listar_instrumentos() if i.codigo == "PAQ-019")
    assert salvo.localizacao == "Almoxarifado"


def test_renomear_plano_na_janela_editar_plano(janela):
    from calibracao.dados.repositorio import Plano

    repo = janela.repo
    plano = repo.incluir_plano(Plano("Plano PAQ-017"))
    for instrumento in repo.listar_instrumentos():
        if instrumento.codigo in ("PAQ-017", "PAQ-018"):
            instrumento.plano_id = plano
            repo.atualizar_instrumento(instrumento)
    aba = janela.aba_instrumentos
    paq18 = next(i for i in repo.listar_instrumentos() if i.codigo == "PAQ-018")
    aba.mostrar(paq18)
    edicao = aba.criar_janela_edicao(paq18)
    assert not hasattr(edicao, "renomear_plano")  # saiu da janela do instrumento
    edicao.reject()
    janela_plano = aba.painel_plano.criar_janela_edicao()  # botão EDITAR PLANO
    assert janela_plano.renomear_plano.text() == "Renomear plano"
    janela_plano.renomear("Plano dos paquímetros 0-150 mm")
    assert repo.obter_plano(plano).nome == "Plano dos paquímetros 0-150 mm"
    assert janela_plano.titulo.text() == "EDITAR PLANO — Plano dos paquímetros 0-150 mm"
    assert "renomeado" in janela_plano.painel.avisos.text()
    assert aba.valores["plano"].text() == "<b>Plano dos paquímetros 0-150 mm</b>"
    janela_plano.reject()  # Cancelar: o nome novo continua (foi gravado na hora)
    assert "Plano dos paquímetros 0-150 mm" in aba.painel_plano.titulo.text()
    janela_plano = aba.painel_plano.criar_janela_edicao()
    janela_plano.renomear("   ")
    assert "Informe o nome do plano" in janela_plano.painel.avisos.text()
    janela_plano.reject()


def test_icone_de_calendario_do_google_em_todos_os_campos_de_data(janela):
    from pathlib import Path

    from calibracao.interface import tema_icones
    from calibracao.interface.estilo import estilo

    assert (tema_icones.PASTA / "LICENSE").read_text(encoding="utf-8").lstrip().startswith(
        "Apache License")  # a licença vai junto com os ícones
    assert 'fill="#ffffff"' in tema_icones.svg_colorido("calendar_month", "#ffffff")
    assert not tema_icones.icone("calendar_month", "#ffffff").isNull()
    caminho = tema_icones.arquivo_do_icone("calendar_month", "#ffffff")
    assert Path(caminho).is_file() and caminho in estilo()  # setinha das datas do Qt
    edicao = novo_cadastro(janela)
    for botao in (edicao.calendario_compra, edicao.calendario_primeira):
        assert botao.text() == "" and not botao.icon().isNull()


def test_icones_aprovados_nos_botoes_abas_e_avisos(janela):
    from calibracao.interface.componentes import RotuloAviso

    aba = janela.aba_instrumentos
    for botao in (aba.novo, aba.editar, aba.mudar_condicao, aba.lixeira,
                  aba.painel_plano.ver, aba.painel_plano.editar,
                  janela.aba_lixeira.restaurar, janela.aba_lixeira.excluir,
                  janela.aba_calibrar.painel_calibracoes.grafico):
        assert not botao.icon().isNull() and botao.text()  # ícone + texto
    assert all(not janela.abas.tabIcon(i).isNull() for i in range(janela.abas.count()))
    assert aba.busca.actions()  # lupa
    assert janela.cadeado.pixmap() is not None and not janela.cadeado.pixmap().isNull()
    aviso = RotuloAviso()
    aviso.setText("✔ PAQ-018 salvo.")
    assert aviso.text() == "✔ PAQ-018 salvo."  # o texto guardado continua o mesmo
    assert "<img" in super(RotuloAviso, aviso).text()  # na tela, o ícone verde
    aviso.setText("Sem símbolo")
    assert super(RotuloAviso, aviso).text() == "Sem símbolo"
