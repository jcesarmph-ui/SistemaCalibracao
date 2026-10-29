"""Repositório: abertura do banco, cadastro de instrumentos e condição (desativar, reativar…)."""

from datetime import date

import pytest

from calibracao.dados.repositorio import ErroDeValidacao, Instrumento, Repositorio
from calibracao.regras.condicao import Condicao

HOJE = date(2027, 3, 15)


@pytest.fixture
def repo(tmp_path):
    with Repositorio.abrir(tmp_path / "calibracao.db", HOJE) as repositorio:
        yield repositorio


def trena(codigo="TRE-901", **outros):
    return Instrumento(codigo=codigo, tipo="Trena", periodicidade_meses=12, **outros)


def test_abrir_faz_backup_do_dia_antes_de_atualizar(tmp_path):
    banco = tmp_path / "calibracao.db"
    Repositorio.abrir(banco, HOJE).fechar()          # banco novo: nada para copiar ainda
    assert not (tmp_path / "backup").exists()
    Repositorio.abrir(banco, HOJE).fechar()          # banco existente: cópia do dia
    assert (tmp_path / "backup" / "calibracao_2027-03-15.db").exists()


def test_incluir_e_obter(repo):
    novo_id = repo.incluir_instrumento(trena(localizacao="Expedição"))
    salvo = repo.obter_instrumento(novo_id)
    assert (salvo.codigo, salvo.localizacao, salvo.exige_calibracao) == (
        "TRE-901", "Expedição", True)


def test_codigo_repetido_e_recusado(repo):
    repo.incluir_instrumento(trena())
    with pytest.raises(ErroDeValidacao, match="Já existe"):
        repo.incluir_instrumento(trena(" TRE-901 "))


def test_campos_obrigatorios(repo):
    with pytest.raises(ErroDeValidacao) as erro:
        repo.incluir_instrumento(Instrumento(codigo=" ", tipo="", periodicidade_meses=0))
    assert len(erro.value.mensagens) == 3


def test_atualizar(repo):
    instrumento = repo.obter_instrumento(repo.incluir_instrumento(trena()))
    instrumento.exige_calibracao = False
    instrumento.localizacao = "Laboratório"
    instrumento.custo_compra, instrumento.responsavel = 89.9, "Fulano"
    repo.atualizar_instrumento(instrumento)
    salvo = repo.obter_instrumento(instrumento.id)
    assert (salvo.exige_calibracao, salvo.localizacao) == (False, "Laboratório")
    assert (salvo.custo_compra, salvo.responsavel) == (89.9, "Fulano")


def test_custo_negativo_e_recusado(repo):
    with pytest.raises(ErroDeValidacao, match="custo de compra"):
        repo.incluir_instrumento(trena(custo_compra=-1.0))


def test_atualizar_pode_manter_o_proprio_codigo(repo):
    instrumento = repo.obter_instrumento(repo.incluir_instrumento(trena()))
    repo.atualizar_instrumento(instrumento)  # não acusa "código repetido" com ele mesmo


def test_sem_historico_esta_em_uso(repo):
    a = repo.incluir_instrumento(trena())
    assert repo.condicao_atual(a).condicao == Condicao.EM_USO
    assert repo.historico_condicao(a) == []


def test_desativar_tira_da_lista(repo):
    a = repo.incluir_instrumento(trena("TRE-901"))
    repo.incluir_instrumento(trena("TRE-902"))
    repo.desativar_instrumento(a, date(2027, 3, 1), "Fita rompida", HOJE)
    assert [i.codigo for i in repo.listar_instrumentos()] == ["TRE-902"]
    assert len(repo.listar_instrumentos(incluir_desativados=True)) == 2
    atual = repo.condicoes_atuais()[a]
    assert (atual.condicao, atual.data, atual.motivo) == (
        Condicao.DESATIVADO, date(2027, 3, 1), "Fita rompida")


def test_motivo_e_opcional_e_nao_repete_a_condicao(repo):
    a = repo.incluir_instrumento(trena())
    repo.desativar_instrumento(a, HOJE, "  ", HOJE)
    assert repo.condicao_atual(a).motivo is None
    with pytest.raises(ErroDeValidacao, match="já está na condição"):
        repo.desativar_instrumento(a, HOJE, "Perdido", HOJE)


def test_data_obrigatoria_e_nao_futura(repo):
    a = repo.incluir_instrumento(trena())
    with pytest.raises(ErroDeValidacao, match="Informe a data"):
        repo.desativar_instrumento(a, None, None, HOJE)
    with pytest.raises(ErroDeValidacao, match="futuro"):
        repo.desativar_instrumento(a, date(2027, 3, 16), None, HOJE)


def test_reativar_guarda_o_historico(repo):
    a = repo.incluir_instrumento(trena())
    repo.mudar_condicao(a, Condicao.ORIENTACAO_INDICATIVA, date(2026, 12, 1), None, HOJE)
    repo.desativar_instrumento(a, date(2027, 1, 10), "Perdido", HOJE)
    repo.reativar_instrumento(a, date(2027, 2, 5), "Achado no almoxarifado", HOJE)
    assert not repo.esta_desativado(a)
    assert [(m.condicao, m.data, m.motivo) for m in repo.historico_condicao(a)] == [
        (Condicao.ORIENTACAO_INDICATIVA, date(2026, 12, 1), None),
        (Condicao.DESATIVADO, date(2027, 1, 10), "Perdido"),
        (Condicao.EM_USO, date(2027, 2, 5), "Achado no almoxarifado"),
    ]


def test_reativar_valida(repo):
    a = repo.incluir_instrumento(trena())
    with pytest.raises(ErroDeValidacao, match="não está desativado"):
        repo.reativar_instrumento(a, HOJE, None, HOJE)
    repo.desativar_instrumento(a, date(2027, 3, 10), "Perdido", HOJE)
    with pytest.raises(ErroDeValidacao, match="antes da última mudança"):
        repo.reativar_instrumento(a, date(2027, 3, 9), None, HOJE)


def test_localizacao_padronizada_ao_salvar(repo):
    # Pedido do usuário: laboratório e orientação indicativa sempre do mesmo jeito.
    a = repo.incluir_instrumento(trena(localizacao="Reserva Laboratório"))
    assert repo.obter_instrumento(a).localizacao == "Laboratório - Reserva"
    instrumento = repo.obter_instrumento(a)
    instrumento.localizacao = "CT-01 Orientativo"
    repo.atualizar_instrumento(instrumento)
    assert repo.obter_instrumento(a).localizacao == "CT-01 - Orientação indicativa"
