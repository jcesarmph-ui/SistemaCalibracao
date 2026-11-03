"""Sub-aba Calibrações: registrar pela tela, parecer final, Lixeira e gráfico de tendência."""

import os
from datetime import date

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtCore import Qt  # noqa: E402
from PySide6.QtWidgets import QApplication  # noqa: E402

from calibracao.dados.repositorio import (  # noqa: E402
    Instrumento,
    NovaCalibracao,
    Plano,
    PontoMedido,
    PontoPlano,
    Repositorio,
)
from calibracao.interface.aba_calibracoes import (  # noqa: E402
    JanelaNovaCalibracao,
    JanelaVerCalibracao,
    PainelCalibracoes,
    referencia,
)
from calibracao.regras.avaliacao import Resultado  # noqa: E402
from calibracao.regras.condicao import Condicao, ParecerFinal  # noqa: E402

HOJE = date(2026, 10, 29)
J = JanelaNovaCalibracao


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def repo(tmp_path):
    with Repositorio.abrir(tmp_path / "calibracao.db", HOJE) as repositorio:
        yield repositorio


@pytest.fixture
def paquimetro(repo):
    """Paquímetro fictício: 2 pontos ± 0,05 (U 0,01) + 1 verificação visual."""
    plano = repo.incluir_plano(Plano("Plano PAQ-900"))
    for nominal in (30.0, 60.0):
        repo.incluir_ponto(PontoPlano(plano, "NUMERICO", f"{nominal:.2f}", valor_nominal=nominal,
                                      unidade="mm", tolerancia_inferior=-0.05,
                                      tolerancia_superior=0.05, incerteza=0.01))
    repo.incluir_ponto(PontoPlano(plano, "VERIFICACAO", "Aspecto geral"))
    instrumento_id = repo.incluir_instrumento(
        Instrumento("PAQ-900", "Paquímetro", periodicidade_meses=12, plano_id=plano))
    return repo.obter_instrumento(instrumento_id)


def preencher(janela, medidos=("30,01", "60,02"), escolha="Aprovado"):
    for linha, texto in enumerate(medidos):
        janela.tabela.item(linha, J.MEDIDO).setText(texto)
    janela.tabela.cellWidget(2, J.MEDIDO).setCurrentText(escolha)


def test_referencia_em_texto():
    ponto = PontoPlano(1, "NUMERICO", "60", valor_nominal=60.0, unidade="mm",
                       tolerancia_inferior=-0.05, tolerancia_superior=0.05)
    assert referencia(ponto) == "60 mm, tolerância ± 0,05"
    sem_nominal = PontoPlano(1, "NUMERICO", "1º ponto", tolerancia_inferior=-3.0,
                             tolerancia_superior=3.0)
    assert "sem nominal fixo" in referencia(sem_nominal)
    assert referencia(PontoPlano(1, "LIMITE", "Planeza", valor_maximo=2.0, unidade="µm")) == (
        "máx. 2 µm")


def test_resultado_aparece_enquanto_digita(app, repo, paquimetro):
    janela = JanelaNovaCalibracao(repo, paquimetro, HOJE)
    assert "Pendente" in janela.geral.text()
    janela.tabela.item(0, J.MEDIDO).setText("30,045")  # 0,045 + U 0,01 passa de 0,05
    assert janela.tabela.item(0, J.RESULTADO).text() == "Reprovado — acima do limite superior"
    janela.tabela.item(0, J.MEDIDO).setText("trinta")
    assert "não é um número" in janela.tabela.item(0, J.RESULTADO).text()
    # a U do plano já vem preenchida
    assert janela.tabela.item(0, J.INCERTEZA).text() == "0,01"


def test_reprovado_nao_oferece_parecer_aprovado(app, repo, paquimetro):
    janela = JanelaNovaCalibracao(repo, paquimetro, HOJE)
    preencher(janela, medidos=("30,045", "60,0"))
    assert "Reprovado" in janela.geral.text()
    opcoes = [janela.parecer.itemData(i) for i in range(janela.parecer.count())]
    assert opcoes == [None, ParecerFinal.ORIENTACAO_INDICATIVA,
                      ParecerFinal.REPROVADO_DESATIVADO]


def test_salvar_exige_tudo_preenchido_e_o_parecer(app, repo, paquimetro):
    janela = JanelaNovaCalibracao(repo, paquimetro, HOJE)
    janela.salvar_calibracao()
    assert "Ponto 1" in janela.avisos.text()
    preencher(janela)
    janela.salvar_calibracao()
    assert "parecer final" in janela.avisos.text()
    assert repo.listar_calibracoes(paquimetro.id) == []


def test_nao_aplicavel_exige_observacao(app, repo, paquimetro):
    janela = JanelaNovaCalibracao(repo, paquimetro, HOJE)
    preencher(janela, medidos=("30,01", ""))
    janela.tabela.item(1, J.NAO_APLICAVEL).setCheckState(Qt.Checked)
    assert "informe por que" in janela.tabela.item(1, J.RESULTADO).text()
    janela.tabela.item(1, J.OBSERVACAO).setText("Bico danificado")
    assert janela.tabela.item(1, J.RESULTADO).text() == "Não aplicável"
    assert "Aprovado" in janela.geral.text()


def test_registrar_pela_tela_muda_a_condicao(app, repo, paquimetro):
    janela = JanelaNovaCalibracao(repo, paquimetro, HOJE)
    janela.data.setDate(janela.data.date().addDays(-3))
    janela.laboratorio.setText("Lab Fictício")
    janela.custo.setText("R$ 150,00")
    preencher(janela, medidos=("30,045", "60,0"))
    janela.parecer.setCurrentIndex(janela.parecer.findData(ParecerFinal.ORIENTACAO_INDICATIVA))
    janela.motivo.setText("Usar só para conferência")
    janela.salvar_calibracao()
    assert janela.calibracao_id is not None, janela.avisos.text()
    [salva] = repo.listar_calibracoes(paquimetro.id)
    assert (salva.data_calibracao, salva.custo, salva.laboratorio, salva.resultado) == (
        date(2026, 10, 26), 150.0, "Lab Fictício", Resultado.REPROVADO)
    # orientação indicativa não é condição: segue Em uso e ganha a marca na localização
    assert repo.condicao_atual(paquimetro.id).condicao == Condicao.EM_USO
    assert repo.obter_instrumento(paquimetro.id).localizacao.endswith("Orientação indicativa")
    [marca] = repo.historico_indicativa(paquimetro.id)
    assert (marca.marcada, marca.motivo) == (True, "Usar só para conferência")


def registrar(repo, instrumento, data, valores=(30.01, 60.02), parecer=ParecerFinal.APROVADO):
    pontos = repo.listar_pontos(instrumento.plano_id)
    medidos = [PontoMedido(p.id, valor=v, incerteza=0.01)
               for p, v in zip(pontos[:2], valores, strict=True)]
    medidos.append(PontoMedido(pontos[2].id, escolha=Resultado.APROVADO))
    return repo.registrar_calibracao(
        NovaCalibracao(instrumento.id, data, medidos, parecer_final=parecer), HOJE)


def test_painel_lista_ve_e_manda_para_a_lixeira(app, repo, paquimetro):
    registrar(repo, paquimetro, date(2025, 10, 1))
    registrar(repo, paquimetro, date(2026, 10, 1), valores=(30.045, 60.0),
              parecer=ParecerFinal.REPROVADO_DESATIVADO)
    painel = PainelCalibracoes(repo, HOJE)
    painel.mostrar(paquimetro)
    assert painel.tabela.rowCount() == 2
    assert painel.tabela.item(0, 0).text() == "01/10/2026"  # mais recente em cima
    assert not painel.registrar.isEnabled()  # desativado pelo parecer
    ver = JanelaVerCalibracao(repo, paquimetro, painel.selecionada())
    assert ver.tabela.item(0, 4).text() == "30,045"
    painel.descartar(painel.selecionada(), "Registrada por engano")
    painel.mostrar(paquimetro)
    assert painel.tabela.rowCount() == 1
    assert painel.registrar.isEnabled()  # a desativação foi desfeita


def test_tendencia_por_ponto(repo, paquimetro):
    registrar(repo, paquimetro, date(2025, 10, 1))
    registrar(repo, paquimetro, date(2026, 10, 1), valores=(29.98, 60.03))
    series = repo.tendencia(paquimetro.id)
    assert [s.nome for s in series] == ["30.00", "60.00"]
    erros = [round(m.erro, 4) for m in series[0].medicoes]
    assert erros == [0.01, -0.02]
    assert series[0].unidade == "mm"
    assert series[0].medicoes[0].tolerancia_superior == 0.05


def test_grafico_salva_png(app, repo, paquimetro, tmp_path):
    from calibracao.interface.grafico_tendencia import JanelaTendencia
    registrar(repo, paquimetro, date(2025, 10, 1))
    registrar(repo, paquimetro, date(2026, 10, 1), valores=(30.045, 60.0),
              parecer=ParecerFinal.ORIENTACAO_INDICATIVA)
    janela = JanelaTendencia(repo.tendencia(paquimetro.id), "PAQ-900")
    assert janela.ponto.count() == 3                  # todos juntos + 1 por ponto
    assert janela.ponto.currentText().startswith("Todos os pontos juntos")  # o principal
    assert janela.todos and len(janela._desenhados) == 4  # 2 pontos x 2 calibrações
    janela.salvar_png(tmp_path / "todos.png")
    janela.ponto.setCurrentIndex(2)
    assert not janela.todos and len(janela._desenhados) == 2
    imagem = tmp_path / "tendencia.png"
    janela.salvar_png(imagem)
    assert imagem.read_bytes()[:4] == b"\x89PNG"


def test_todos_juntos_mesma_tolerancia_fica_em_erro(app, repo, paquimetro):
    from calibracao.interface.grafico_tendencia import JanelaTendencia, tolerancia_comum
    registrar(repo, paquimetro, date(2025, 10, 1))
    registrar(repo, paquimetro, date(2026, 10, 1))
    series = repo.tendencia(paquimetro.id)
    assert tolerancia_comum(series)
    janela = JanelaTendencia(series, "PAQ-900")
    assert "eixo em erro" in janela._eixo.get_title()
    # os dois pontos da mesma data ficam um pouco afastados para o lado
    mesma_data = [d.x for d in janela._desenhados if d.medicao.data == date(2025, 10, 1)]
    assert len(set(mesma_data)) == 2
    # clicar no nome na legenda esconde o ponto; clicar de novo mostra
    janela.esconder_ou_mostrar(0)
    assert not any(a.get_visible() for a in janela._grupos[0])
    assert janela._itens_legenda[0][1].get_alpha() == 0.3
    janela.esconder_ou_mostrar(0)
    assert all(a.get_visible() for a in janela._grupos[0])


def test_todos_juntos_tolerancias_diferentes_fica_em_porcentagem(app):
    from calibracao.dados.repositorio import MedicaoTendencia, SerieTendencia
    from calibracao.interface.grafico_tendencia import JanelaTendencia, em_porcentagem
    assert em_porcentagem(0.01, -0.02, 0.05) == pytest.approx(20)    # lado de cima: 0,05
    assert em_porcentagem(-0.01, -0.02, 0.05) == pytest.approx(-50)  # lado de baixo: 0,02
    assert em_porcentagem(-0.01, None, 0.05) == pytest.approx(-20)   # falta um lado: o outro
    assert em_porcentagem(0.01, None, None) is None
    ok, dia = Resultado.APROVADO, date(2025, 1, 1)
    series = [
        SerieTendencia("1 kg", "g", [MedicaoTendencia(dia, 0.5, 0.1, -1, 1, ok)]),
        SerieTendencia("20 kg", "g", [MedicaoTendencia(dia, 5, 1, -10, 10, ok)]),
        SerieTendencia("Sem tol.", "g", [MedicaoTendencia(dia, 1, 1, None, None, ok)]),
    ]
    janela = JanelaTendencia(series, "BAL-900")
    assert "% da tolerância" in janela._eixo.get_title()
    assert [round(d.y) for d in janela._desenhados] == [50, 50]
    assert "Sem tol." in janela.aviso.text()   # sem tolerância: fora, e avisado


def test_cor_e_marcador_nao_se_repetem():
    from calibracao.interface.grafico_tendencia import cor_e_marcador
    assert len({cor_e_marcador(i) for i in range(20)}) == 20


def test_grafico_sem_dados(app):
    from calibracao.interface.grafico_tendencia import JanelaTendencia
    janela = JanelaTendencia([], "PAQ-900")
    assert not janela.exportar.isEnabled()


def test_corrigir_pela_tela_vem_preenchido_e_registra_a_correcao(app, repo, paquimetro):
    calibracao_id = registrar(repo, paquimetro, date(2026, 10, 20))
    painel = PainelCalibracoes(repo, HOJE)
    painel.usuario = "maria.silva - PC-LAB"
    painel.mostrar(paquimetro)
    [salva] = repo.listar_calibracoes(paquimetro.id)
    # a calibração abre só para ver; EDITAR (modo edição) leva à correção
    ver = JanelaVerCalibracao(repo, paquimetro, salva, pode_editar=True)
    assert not ver.editar.isHidden()
    ver.editar.click()
    assert ver.result() == JanelaVerCalibracao.EDITAR
    janela = JanelaNovaCalibracao(repo, paquimetro, HOJE, corrigir=salva,
                                  usuario=painel.usuario)
    # vem como foi salva, com a data travada
    assert not janela.data.isEnabled()
    assert janela.data.date().toPython() == date(2026, 10, 20)
    assert janela.tabela.item(0, J.MEDIDO).text() == "30,01"
    assert janela.tabela.cellWidget(2, J.MEDIDO).currentText() == "Aprovado"
    assert janela.parecer.currentData() == ParecerFinal.APROVADO
    assert janela.salvar.text() == "SALVAR CORREÇÃO"
    # corrige o certificado e um valor
    janela.certificado.setText("CERT-77")
    janela.tabela.item(1, J.MEDIDO).setText("60,03")
    janela.salvar_calibracao()
    assert janela.result(), janela.avisos.text()
    corrigida = repo.obter_calibracao(calibracao_id)
    assert corrigida.certificado == "CERT-77"
    assert repo.pontos_da_calibracao(calibracao_id)[1].valor == 60.03
    [registro] = repo.listar_correcoes(calibracao_id)
    assert registro.usuario == "maria.silva - PC-LAB"
    assert len(registro.mudancas) == 2
    # "Ver calibração" mostra a correção
    ver = JanelaVerCalibracao(repo, paquimetro, corrigida)
    assert ver.tabela_correcoes.rowCount() == 2


def test_corrigir_sem_mudar_nada_avisa(app, repo, paquimetro):
    registrar(repo, paquimetro, date(2026, 10, 20))
    [salva] = repo.listar_calibracoes(paquimetro.id)
    janela = JanelaNovaCalibracao(repo, paquimetro, HOJE, corrigir=salva, usuario="x")
    janela.salvar_calibracao()
    assert "Nada foi alterado" in janela.avisos.text()


def test_modo_consulta_esconde_editar_e_nova_calibracao(app, repo, paquimetro):
    registrar(repo, paquimetro, date(2026, 10, 20))
    painel = PainelCalibracoes(repo, HOJE)
    painel.definir_edicao(False)
    assert painel.registrar.isHidden()
    [salva] = repo.listar_calibracoes(paquimetro.id)
    ver = JanelaVerCalibracao(repo, paquimetro, salva, pode_editar=painel.pode_editar)
    assert ver.editar.isHidden()


def test_ponto_com_u_nao_se_aplica_na_janela(app, repo):
    """"-"/"N/A" na DQ05 (2026-11-03): a U aparece "não se aplica" e o ponto é avaliado."""
    plano = repo.incluir_plano(Plano("Plano MIC-901"))
    repo.incluir_ponto(PontoPlano(plano, "LIMITE", "Planeza", valor_maximo=2.0,
                                  incerteza_nao_aplica=True))
    mic = repo.obter_instrumento(repo.incluir_instrumento(Instrumento(
        "MIC-901", "Micrômetro", plano_id=plano, periodicidade_meses=12)))
    janela = JanelaNovaCalibracao(repo, mic, HOJE)
    assert janela.tabela.item(0, J.INCERTEZA).text() == "não se aplica"
    janela.tabela.item(0, J.MEDIDO).setText("0,64")
    assert janela.resultados() == [Resultado.APROVADO]
