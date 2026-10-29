"""Trava de edição: dois computadores abrindo o mesmo banco da pasta de rede."""

from datetime import datetime, timedelta

import pytest

from calibracao.dados.repositorio import (
    MENSAGEM_CONSULTA,
    ErroDeValidacao,
    Instrumento,
    Repositorio,
)
from calibracao.regras.trava import ObservadorDeSinal, sinal_antigo

HOJE = datetime(2026, 10, 29, 14, 0)


@pytest.fixture
def dois_pcs(tmp_path):
    banco = tmp_path / "calibracao.db"
    a = Repositorio.abrir(banco, HOJE.date())
    b = Repositorio.abrir(banco, HOJE.date())
    yield a, b
    a.fechar()
    b.fechar()


def test_observador_ve_sinal_parado():
    observador = ObservadorDeSinal()
    observador.ver(5, HOJE)
    observador.ver(5, HOJE + timedelta(minutes=1))
    assert not observador.parado(HOJE + timedelta(minutes=1))
    assert observador.parado(HOJE + timedelta(minutes=2))
    observador.ver(6, HOJE + timedelta(minutes=2))  # voltou a dar sinal
    assert not observador.parado(HOJE + timedelta(minutes=3))


def test_sinal_antigo():
    assert not sinal_antigo(HOJE, HOJE + timedelta(minutes=10))
    assert sinal_antigo(HOJE, HOJE + timedelta(minutes=11))


def test_primeiro_edita_segundo_consulta(dois_pcs):
    a, b = dois_pcs
    assert a.tentar_editar("ana", "PC-1", HOJE) is None
    dono = b.tentar_editar("beto", "PC-2", HOJE)
    assert (dono.usuario, dono.computador, dono.desde) == ("ana", "PC-1", HOJE)
    assert b.modo_consulta and not a.modo_consulta


def test_modo_consulta_nao_grava_nada(dois_pcs):
    a, b = dois_pcs
    a.tentar_editar("ana", "PC-1", HOJE)
    b.tentar_editar("beto", "PC-2", HOJE)
    with pytest.raises(ErroDeValidacao, match="Modo consulta"):
        b.incluir_instrumento(Instrumento("TRE-1", "Trena"))
    assert MENSAGEM_CONSULTA
    a.incluir_instrumento(Instrumento("TRE-1", "Trena"))
    assert [i.codigo for i in b.listar_instrumentos()] == ["TRE-1"]  # mas vê o que A salvou


def test_fechar_libera_para_o_outro(dois_pcs):
    a, b = dois_pcs
    a.tentar_editar("ana", "PC-1", HOJE)
    b.tentar_editar("beto", "PC-2", HOJE)
    a.liberar_trava()
    assert b.obter_trava() is None
    assert b.tentar_editar("beto", "PC-2", HOJE + timedelta(minutes=1)) is None
    assert not b.modo_consulta


def test_sinal_parado_deixa_assumir(dois_pcs):
    a, b = dois_pcs
    a.tentar_editar("ana", "PC-1", HOJE)
    dono = b.tentar_editar("beto", "PC-2", HOJE)
    # com sinal diferente do visto (A ainda está viva), não toma
    a.dar_sinal(HOJE + timedelta(seconds=30))
    assert b.tentar_editar("beto", "PC-2", HOJE + timedelta(minutes=2),
                           assumir_sinal=dono.sinal) is not None
    # A parou de dar sinal: B assume com o sinal que viu parado
    parado = b.obter_trava().sinal
    assert b.tentar_editar("beto", "PC-2", HOJE + timedelta(minutes=3),
                           assumir_sinal=parado) is None
    # A volta (o PC tinha travado): perde a trava e vira consulta
    assert not a.dar_sinal(HOJE + timedelta(minutes=4))
    assert a.modo_consulta


def test_trava_esquecida_de_ontem_vence_sozinha(dois_pcs):
    a, b = dois_pcs
    a.tentar_editar("ana", "PC-1", HOJE - timedelta(days=1))
    assert b.tentar_editar("beto", "PC-2", HOJE) is None


def test_mesma_pessoa_no_mesmo_pc_retoma(dois_pcs):
    a, b = dois_pcs  # b = o programa aberto de novo depois de fechar sem liberar
    a.tentar_editar("ana", "PC-1", HOJE)
    assert b.tentar_editar("ana", "PC-1", HOJE + timedelta(minutes=1)) is None
