"""Repositório: abertura do banco, cadastro de instrumentos, desativação e reativação."""

from datetime import date

import pytest

from calibracao.dados.repositorio import ErroDeValidacao, Instrumento, Repositorio

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
    repo.atualizar_instrumento(instrumento)
    salvo = repo.obter_instrumento(instrumento.id)
    assert (salvo.exige_calibracao, salvo.localizacao) == (False, "Laboratório")


def test_atualizar_pode_manter_o_proprio_codigo(repo):
    instrumento = repo.obter_instrumento(repo.incluir_instrumento(trena()))
    repo.atualizar_instrumento(instrumento)  # não acusa "código repetido" com ele mesmo


def test_desativar_tira_da_lista_e_vai_para_desativados(repo):
    a = repo.incluir_instrumento(trena("TRE-901"))
    repo.incluir_instrumento(trena("TRE-902"))
    repo.desativar_instrumento(a, date(2027, 3, 1), "Fita rompida", HOJE)
    assert [i.codigo for i in repo.listar_instrumentos()] == ["TRE-902"]
    assert len(repo.listar_instrumentos(incluir_desativados=True)) == 2
    [(instrumento, desativacao)] = repo.listar_desativados()
    assert (instrumento.codigo, desativacao.data, desativacao.motivo) == (
        "TRE-901", date(2027, 3, 1), "Fita rompida")


def test_desativar_exige_motivo_e_nao_repete(repo):
    a = repo.incluir_instrumento(trena())
    with pytest.raises(ErroDeValidacao, match="motivo"):
        repo.desativar_instrumento(a, HOJE, "  ", HOJE)
    repo.desativar_instrumento(a, HOJE, "Perdido", HOJE)
    with pytest.raises(ErroDeValidacao, match="já está desativado"):
        repo.desativar_instrumento(a, HOJE, "Perdido", HOJE)


def test_reativar_guarda_a_historia(repo):
    a = repo.incluir_instrumento(trena())
    repo.desativar_instrumento(a, date(2027, 1, 10), "Perdido", HOJE)
    repo.reativar_instrumento(a, date(2027, 2, 5))
    assert not repo.esta_desativado(a)
    assert repo.listar_desativados() == []
    [historia] = repo.historico_desativacoes(a)
    assert (historia.data, historia.motivo, historia.reativado_em) == (
        date(2027, 1, 10), "Perdido", date(2027, 2, 5))


def test_reativar_valida(repo):
    a = repo.incluir_instrumento(trena())
    with pytest.raises(ErroDeValidacao, match="não está desativado"):
        repo.reativar_instrumento(a, HOJE)
    repo.desativar_instrumento(a, date(2027, 3, 10), "Perdido", HOJE)
    with pytest.raises(ErroDeValidacao, match="antes da desativação"):
        repo.reativar_instrumento(a, date(2027, 3, 9))


def test_localizacao_padronizada_ao_salvar(repo):
    # Pedido do usuário: laboratório e orientação indicativa sempre do mesmo jeito.
    a = repo.incluir_instrumento(trena(localizacao="Reserva Laboratório"))
    assert repo.obter_instrumento(a).localizacao == "Laboratório - Reserva"
    instrumento = repo.obter_instrumento(a)
    instrumento.localizacao = "CT-01 Orientativo"
    repo.atualizar_instrumento(instrumento)
    assert repo.obter_instrumento(a).localizacao == "CT-01 - Orientação indicativa"
