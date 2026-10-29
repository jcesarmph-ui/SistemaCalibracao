"""Modo consulta na tela: duas janelas (dois computadores) no mesmo banco."""

import os
from datetime import date

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtWidgets import QApplication  # noqa: E402

from calibracao.dados.repositorio import Instrumento, Plano, PontoPlano, Repositorio  # noqa: E402
from calibracao.interface.janela import JanelaPrincipal  # noqa: E402

HOJE = date(2026, 10, 29)


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def duas_janelas(app, tmp_path):
    banco = tmp_path / "calibracao.db"
    with Repositorio.abrir(banco, HOJE) as repo:
        plano = repo.incluir_plano(Plano("Plano TRE-901"))
        repo.incluir_ponto(PontoPlano(plano, "VERIFICACAO", "Aspecto geral"))
        repo.incluir_instrumento(Instrumento("TRE-901", "Trena", plano_id=plano,
                                             periodicidade_meses=12))
    repo_a, repo_b = Repositorio.abrir(banco, HOJE), Repositorio.abrir(banco, HOJE)
    a = JanelaPrincipal(repo_a, tmp_path, HOJE, identidade=("ana", "PC-1"))
    b = JanelaPrincipal(repo_b, tmp_path, HOJE, identidade=("beto", "PC-2"))
    yield a, b
    for janela in (a, b):
        janela.close()
        janela.repo.fechar()


def visivel(widget):
    return not widget.isHidden()  # as janelas do teste não aparecem na tela


def test_quem_abre_depois_so_consulta(duas_janelas):
    a, b = duas_janelas
    assert a.rotulo_modo.text() == "Modo edição"
    assert b.rotulo_modo.text() == "Modo consulta - ana - PC-1"
    assert "SOMENTE CONSULTA" in b.windowTitle()
    aba = b.aba_instrumentos
    for botao in (aba.novo, aba.salvar, aba.mudar_condicao, aba.lixeira,
                  aba.painel_plano.salvar, aba.painel_calibracoes.registrar,
                  b.aba_lixeira.restaurar):
        assert not visivel(botao)
    assert aba.campos["codigo"].isReadOnly()
    aba.tabela.selectRow(0)
    assert aba.titulo_dados.text() == "Consultando TRE-901"
    assert visivel(aba.painel_calibracoes.grafico)  # consultar continua liberado
    assert visivel(a.aba_instrumentos.salvar)


def test_consulta_ve_o_que_o_outro_salvou(duas_janelas):
    a, b = duas_janelas
    a.repo.incluir_instrumento(Instrumento("TRE-902", "Trena"))
    b.a_cada_sinal()  # 30 segundos depois
    assert b.valores_indicadores["instrumentos"].text() == "2"
    assert b.repo.modo_consulta  # A continua editando


def test_quando_o_outro_fecha_passa_sozinho_para_edicao(duas_janelas):
    a, b = duas_janelas
    a.close()
    b.a_cada_sinal()
    assert b.rotulo_modo.text() == "Modo edição"
    assert visivel(b.aba_instrumentos.salvar)
    assert not b.aba_instrumentos.campos["codigo"].isReadOnly()


def test_quando_o_outro_para_de_responder_assume(duas_janelas):
    from datetime import timedelta
    a, b = duas_janelas
    a.relogio.stop()                       # o PC de A travou: não dá mais sinal
    b.a_cada_sinal()
    assert b.repo.modo_consulta            # ainda não: precisa ficar 2 minutos parado
    b.observador._desde -= timedelta(minutes=2)
    b.a_cada_sinal()
    assert b.rotulo_modo.text() == "Modo edição"
    a.a_cada_sinal()                       # A volta: percebe que perdeu e vira consulta
    assert a.rotulo_modo.text() == "Modo consulta - beto - PC-2"
    assert not visivel(a.aba_instrumentos.salvar)


def test_parado_30_minutos_libera_a_edicao(duas_janelas):
    from datetime import timedelta
    a, b = duas_janelas
    a.ultima_atividade -= timedelta(minutes=31)
    a.a_cada_sinal()
    assert a.rotulo_modo.text() == "Modo consulta"
    a.a_cada_sinal()                       # sem mexer no programa, não pega de volta sozinha
    assert a.repo.modo_consulta
    b.a_cada_sinal()                       # B estava consultando: passa para edição
    assert b.rotulo_modo.text() == "Modo edição"


def test_parado_volta_a_editar_ao_mexer_se_estiver_livre(duas_janelas):
    from datetime import timedelta
    a, b = duas_janelas
    b.close()
    a.ultima_atividade -= timedelta(minutes=31)
    a.a_cada_sinal()
    assert a.repo.modo_consulta
    a.ultima_atividade = a.agora()         # a pessoa voltou e mexeu no mouse
    a.a_cada_sinal()
    assert a.rotulo_modo.text() == "Modo edição"


def test_parado_com_algo_digitado_nao_libera(duas_janelas):
    from datetime import timedelta
    a, _ = duas_janelas
    aba = a.aba_instrumentos
    aba.tabela.selectRow(0)
    aba.campos["faixa"].setText("0-5 m")  # digitado e não salvo
    a.ultima_atividade -= timedelta(minutes=31)
    a.a_cada_sinal()
    assert a.rotulo_modo.text() == "Modo edição"
    assert a.repo.obter_trava().usuario == "ana"


def test_pedir_edicao_e_quem_edita_libera(duas_janelas):
    a, b = duas_janelas
    b.pedir_edicao()                       # clique no texto do canto
    assert b.rotulo_modo.text() == "Modo consulta - ana - PC-1 - pedido enviado"
    a.verificar_pedido()                   # até 5 s depois, A recebe o aviso
    assert a.caixa_pedido is not None
    assert "beto (PC-2) pediu para editar" in a.caixa_pedido.text()
    a.responder_pedido(liberar=True)
    assert a.rotulo_modo.text() == "Modo consulta"
    b.verificar_pedido()                   # B vê que foi liberado e passa para edição
    assert b.rotulo_modo.text() == "Modo edição"
    a.a_cada_sinal()                       # A não pega de volta sozinha
    assert a.rotulo_modo.text() == "Modo consulta - beto - PC-2"


def test_quem_edita_pode_recusar(duas_janelas):
    a, b = duas_janelas
    b.pedir_edicao()
    a.verificar_pedido()
    a.verificar_pedido()                   # o mesmo pedido não abre dois avisos
    a.responder_pedido(liberar=False)
    assert a.rotulo_modo.text() == "Modo edição"
    b.verificar_pedido()
    assert b.rotulo_modo.text() == "Modo consulta - ana - PC-1 - pedido recusado"


def test_aviso_lembra_de_salvar_antes(duas_janelas):
    a, b = duas_janelas
    aba = a.aba_instrumentos
    aba.tabela.selectRow(0)
    aba.campos["faixa"].setText("0-5 m")   # digitado e não salvo
    b.pedir_edicao()
    a.verificar_pedido()
    assert "não salvas" in a.caixa_pedido.text()


def test_ninguem_editando_clicar_ja_passa_para_edicao(duas_janelas):
    a, b = duas_janelas
    a.close()
    b.pedir_edicao()
    assert b.rotulo_modo.text() == "Modo edição"
