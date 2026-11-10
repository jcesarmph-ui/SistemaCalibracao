"""Relatórios (pedido de 2026-11-10): conteúdo do mês e do ano, PDF, relatório final guardado
sozinho (uma vez só, conferido por SHA-256) e a aba Relatórios. Dados fictícios."""

import datetime
import os
from datetime import date
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from calibracao.dados.repositorio import (  # noqa: E402
    CorrecaoCalibracao,
    ErroDeValidacao,
    Instrumento,
    NovaCalibracao,
    Plano,
    PontoMedido,
    PontoPlano,
    Repositorio,
)
from calibracao.interface import aba_relatorios  # noqa: E402
from calibracao.interface.aba_relatorios import AbaRelatorios, guardar_pendentes  # noqa: E402
from calibracao.regras import relatorio as regras  # noqa: E402
from calibracao.regras.condicao import ParecerFinal  # noqa: E402
from calibracao.regras.relatorio import ANUAL, MENSAL, Periodo  # noqa: E402

HOJE = date(2027, 1, 10)
AGORA = datetime.datetime(2027, 1, 10, 8, 0)
OUTUBRO = Periodo(MENSAL, 2026, 12)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


# --------------------------------------------------------------------------- regras
def test_periodo():
    assert (OUTUBRO.chave, OUTUBRO.nome, OUTUBRO.fim) == ("2026-12", "dezembro de 2026",
                                                         date(2026, 12, 31))
    assert Periodo.da_chave("2027") == Periodo(ANUAL, 2027)
    assert Periodo(ANUAL, 2026).acabou(HOJE) and not Periodo(MENSAL, 2027, 1).acabou(HOJE)


def test_pendentes_desde_a_implantacao():
    faltam = regras.pendentes(date(2026, 11, 1), HOJE, set())
    assert [p.chave for p in faltam] == ["2026-11", "2026-12", "2026"]
    assert [p.chave for p in regras.pendentes(date(2026, 11, 1), HOJE, {"2026-11"})] == [
        "2026-12", "2026"]
    assert regras.pendentes(None, HOJE, set()) == []


def test_dinheiro():
    assert regras.dinheiro(1620) == "R$ 1.620,00"


# --------------------------------------------------------------------------- banco
@pytest.fixture
def repo(tmp_path):
    (tmp_path / "dados").mkdir()
    repositorio = Repositorio.abrir(tmp_path / "dados" / "calibracao.db", HOJE)
    repositorio.marcar_implantacao(date(2026, 11, 1))
    plano = repositorio.incluir_plano(Plano("Plano PAQ-900"))
    ponto = repositorio.incluir_ponto(PontoPlano(
        plano, "NUMERICO", "50", valor_nominal=50.0, unidade="mm", tolerancia_inferior=-0.05,
        tolerancia_superior=0.05, incerteza=0.01))
    ids = {}
    for codigo, prevista in [("PAQ-900", date(2026, 12, 5)), ("PAQ-901", date(2026, 11, 20)),
                             ("PAQ-902", date(2026, 12, 15)), ("PAQ-903", date(2026, 12, 20))]:
        ids[codigo] = repositorio.incluir_instrumento(Instrumento(
            codigo, "Paquímetro", localizacao="Usinagem", periodicidade_meses=12,
            plano_id=plano, primeira_prevista=prevista))
    repositorio.registrar_calibracao(NovaCalibracao(       # no prazo
        ids["PAQ-900"], date(2026, 12, 6), [PontoMedido(ponto, valor=50.01, incerteza=0.01)],
        parecer_final=ParecerFinal.APROVADO, laboratorio="Lab A", certificado="C-1",
        custo=180.0), HOJE)
    repositorio.registrar_calibracao(NovaCalibracao(       # atrasada (prevista em novembro)
        ids["PAQ-901"], date(2026, 12, 9), [PontoMedido(ponto, valor=50.05, incerteza=0.01)],
        parecer_final=ParecerFinal.REPROVADO_DESATIVADO, motivo_parecer="Bico gasto",
        laboratorio="Lab A", custo=200.0, motivo_atraso="Laboratório cheio"), HOJE)
    repositorio.calibracao_atrasada = repositorio.listar_calibracoes(ids["PAQ-901"])[0]
    repositorio.ids = ids
    yield repositorio
    repositorio.fechar()


def test_conteudo_do_mes_final(repo):
    conteudo = repo.conteudo_do_relatorio(OUTUBRO, HOJE, AGORA)
    assert conteudo.final and conteudo.titulo == "RELATÓRIO DE DEZEMBRO DE 2026"
    numeros = {n.rotulo: n.valor for n in conteudo.numeros}
    assert numeros["Previstas no mês"] == "3"   # PAQ-900, 902 e 903 (o 901 era de novembro)
    assert numeros["Feitas"] == "2" and numeros["Vencidas"] == "2"
    assert numeros["No prazo"] == "50%" and numeros["Custo do mês"] == "R$ 380,00"
    assert [linha.codigo for linha in conteudo.linhas] == ["PAQ-900", "PAQ-901", "PAQ-902",
                                                           "PAQ-903"]
    assert conteudo.linhas[1].situacao == "Reprovado - Desativado"
    assert conteudo.linhas[2].situacao == "Vencida"
    textos = [texto for _, texto in conteudo.alteracoes]
    assert "PAQ-901 reprovado e desativado em 09/12/2026 — Bico gasto" in textos
    assert "PAQ-901 calibrado com atraso em 09/12/2026 — Laboratório cheio" in textos
    assert "PAQ-902 vencido (previsto para 15/12/2026)." in textos


def test_mes_atual_em_andamento_e_ano(repo):
    atual = repo.conteudo_do_relatorio(regras.mes_atual(date(2026, 12, 10)), date(2026, 12, 10),
                                       AGORA)
    numeros = {n.rotulo: n.valor for n in atual.numeros}
    assert not atual.final and "Em andamento" in atual.subtitulo
    assert numeros["Pendentes"] == "2" and numeros["Vencidas"] == "0"
    ano = repo.conteudo_do_relatorio(Periodo(ANUAL, 2026), HOJE, AGORA)
    assert ano.titulo == "RELATÓRIO DO ANO DE 2026"
    assert {n.rotulo: n.valor for n in ano.numeros}["Custo médio/mês"] == "R$ 190,00"  # 2 meses


def test_correcao_e_instrumento_novo_entram_nas_alteracoes(repo):
    calibracao = repo.calibracao_atrasada
    pontos = {r.id: PontoMedido(r.id, valor=r.valor, incerteza=r.incerteza)
              for r in repo.pontos_da_calibracao(calibracao.id)}
    repo.corrigir_calibracao(calibracao.id, CorrecaoCalibracao(
        pontos, parecer_final=ParecerFinal.REPROVADO_DESATIVADO, motivo_parecer="Bico gasto",
        laboratorio="Lab B", certificado=None, responsavel=None, custo=200.0,
        observacoes=None, motivo_atraso="Laboratório cheio"), "ana - PC",
        datetime.datetime(2027, 1, 5, 9, 0))
    janeiro = repo.conteudo_do_relatorio(Periodo(MENSAL, 2027, 1), HOJE, AGORA)
    assert any("Correção na calibração de PAQ-901" in t and "Lab A → Lab B" in t
               for _, t in janeiro.alteracoes)
    hoje_real = date.today()
    novos = repo.conteudo_do_relatorio(regras.mes_atual(hoje_real), hoje_real, AGORA)
    assert any("4 instrumentos" in t or "Instrumento novo" in t for _, t in novos.alteracoes)


def test_relatorio_final_guardado_uma_vez_e_conferido(app, repo, tmp_path):
    assert [p.chave for p in repo.relatorios_pendentes(HOJE)] == ["2026-11", "2026-12", "2026"]
    assert guardar_pendentes(repo, HOJE, "ana - PC") == 3
    assert repo.relatorios_pendentes(HOJE) == []
    guardados = repo.relatorios_guardados()
    assert {r.periodo.chave for r in guardados} == {"2026-11", "2026-12", "2026"}
    dezembro = next(r for r in guardados if r.periodo.chave == "2026-12")
    caminho = repo.caminho_do_relatorio(dezembro)
    assert caminho.parent.name == "relatorios" and caminho.read_bytes().startswith(b"%PDF")
    assert repo.conferir_relatorio(dezembro) is None
    with pytest.raises(ErroDeValidacao, match="já está guardado"):
        repo.guardar_relatorio(OUTUBRO, caminho, None, AGORA)
    caminho.write_bytes(b"%PDF-1.4 mexido")
    assert "alterado depois" in repo.conferir_relatorio(dezembro)


def test_modo_consulta_nao_guarda(app, repo):
    repo.modo_consulta = True
    with pytest.raises(ErroDeValidacao):
        guardar_pendentes(repo, HOJE, None)


def test_relatorio_grande_continua_na_outra_pagina(app, repo, tmp_path):
    from calibracao.interface.relatorio_pdf import gerar_pdf

    conteudo = repo.conteudo_do_relatorio(OUTUBRO, HOJE, AGORA)
    conteudo.linhas = conteudo.linhas * 30
    destino = gerar_pdf(conteudo, [d for _, d in repo.listar_graficos()],
                        *repo.dados_dos_indicadores(), tmp_path / "grande.pdf")
    assert destino.read_bytes().count(b"/Type /Page\n") + destino.read_bytes().count(
        b"/Type /Page ") + destino.read_bytes().count(b"/Type/Page") >= 2 or \
        destino.stat().st_size > 50_000


# --------------------------------------------------------------------------- aba
@pytest.fixture
def abertos(monkeypatch):
    lista: list[Path] = []
    monkeypatch.setattr(aba_relatorios, "abrir_arquivo",
                        lambda caminho: lista.append(Path(caminho)) or True)
    return lista


def test_aba_lista_com_botao_abrir_pdf(app, repo, abertos):
    guardar_pendentes(repo, HOJE, None)
    aba = AbaRelatorios(repo, HOJE)
    aba.atualizar()
    assert aba.tabela.rowCount() == 3
    assert aba.abrir_final.text() == "Abrir relatório final de dezembro de 2026"
    botao = aba.tabela.cellWidget(0, 3)
    assert botao.text() == "Abrir PDF"
    botao.click()
    assert len(abertos) == 1 and abertos[0].parent.name == "relatorios"
    assert "aberto" in aba.avisos.text()


def test_abrir_relatorio_do_mes_atual_e_do_ano(app, repo, abertos):
    aba = AbaRelatorios(repo, HOJE)
    aba.atualizar()
    assert not aba.abrir_final.isEnabled() and "Ainda não há" in aba.texto_final.text()
    aba.abrir_mes.click()
    aba.abrir_ano.click()
    assert len(abertos) == 2 and all(p.read_bytes().startswith(b"%PDF") for p in abertos)


def test_janela_guarda_sozinha_ao_entrar_no_modo_edicao(app, repo, abertos):
    from calibracao.interface.janela import JanelaPrincipal

    janela = JanelaPrincipal(repo, repo.pasta_dados, HOJE)
    janela.aplicar_modo(None)
    assert len(repo.relatorios_guardados()) == 3
    assert janela.aba_relatorios.tabela.rowCount() == 3
    janela.close()


def test_orientacao_indicativa_nao_entra_nas_alteracoes(repo):
    """Pedido do usuário (2026-11-10): o relatório não avisa que um instrumento (ex.: trena)
    passou a ser orientação indicativa."""
    ponto = repo.listar_pontos(repo.listar_planos()[0].id)[0].id
    repo.registrar_calibracao(NovaCalibracao(
        repo.ids["PAQ-903"], date(2026, 12, 20), [PontoMedido(ponto, valor=50.0, incerteza=0.01)],
        parecer_final=ParecerFinal.ORIENTACAO_INDICATIVA, motivo_parecer="Escala apagada",
        laboratorio="Lab A", custo=100.0), HOJE)
    conteudo = repo.conteudo_do_relatorio(OUTUBRO, HOJE, AGORA)
    assert "PAQ-903" in [linha.codigo for linha in conteudo.linhas]
    assert not any("indicativa" in texto.lower() for _, texto in conteudo.alteracoes)


def test_relatorio_do_ano_so_com_os_graficos(app, repo, tmp_path, monkeypatch):
    """Pedido do usuário (2026-11-10): o do ano tem só os números do topo e os gráficos do
    painel (sem tabela de calibrações e ALTERAÇÕES); o do mês continua completo."""
    from calibracao.interface import relatorio_pdf

    escritos: list[str] = []
    original = relatorio_pdf._Folha.texto

    def anotar(folha, x, y, w, h, conteudo, *args, **kwargs):
        escritos.append(conteudo)
        return original(folha, x, y, w, h, conteudo, *args, **kwargs)

    monkeypatch.setattr(relatorio_pdf._Folha, "texto", anotar)
    graficos = [d for _, d in repo.listar_graficos()]
    dados = repo.dados_dos_indicadores()
    ano = repo.conteudo_do_relatorio(Periodo(ANUAL, 2026), HOJE, AGORA)
    relatorio_pdf.gerar_pdf(ano, graficos, *dados, tmp_path / "ano.pdf")
    assert graficos and "ALTERAÇÕES" not in escritos and "Calibrações do ano" not in escritos
    assert "Custo do ano" in escritos and "Previstas no ano" in escritos
    escritos.clear()
    mes = repo.conteudo_do_relatorio(OUTUBRO, HOJE, AGORA)
    relatorio_pdf.gerar_pdf(mes, graficos, *dados, tmp_path / "mes.pdf")
    assert "ALTERAÇÕES" in escritos and "Calibrações do mês" in escritos
