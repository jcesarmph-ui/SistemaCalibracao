"""Repositório: registro de calibrações (regras da fase 2 + banco)."""

from datetime import date

import pytest

from calibracao.dados.repositorio import (
    ErroDeValidacao,
    Instrumento,
    NovaCalibracao,
    Plano,
    PontoMedido,
    PontoPlano,
    Repositorio,
)
from calibracao.regras.avaliacao import Resultado

HOJE = date(2027, 3, 15)


@pytest.fixture
def repo(tmp_path):
    with Repositorio.abrir(tmp_path / "calibracao.db", HOJE) as repositorio:
        yield repositorio


@pytest.fixture
def paquimetro(repo):
    """Paquímetro fictício: 2 pontos numéricos (± 0,05, U 0,01) + 1 verificação visual."""
    plano = repo.incluir_plano(Plano("Plano PAQ-900"))
    for nominal in (30.0, 60.0):
        repo.incluir_ponto(PontoPlano(plano, "NUMERICO", f"{nominal}", valor_nominal=nominal,
                                      tolerancia_inferior=-0.05, tolerancia_superior=0.05,
                                      incerteza=0.01))
    repo.incluir_ponto(PontoPlano(plano, "VERIFICACAO", "Aspecto geral"))
    instrumento = repo.incluir_instrumento(
        Instrumento("PAQ-900", "Paquímetro", periodicidade_meses=12, plano_id=plano))
    return instrumento, [p.id for p in repo.listar_pontos(plano)]


def calibracao(instrumento, pontos, valores=(30.01, 60.02), escolha=Resultado.APROVADO,
               data=date(2027, 3, 10)):
    medidos = [PontoMedido(pid, valor=v, incerteza=0.01)
               for pid, v in zip(pontos[:2], valores, strict=True)]
    medidos.append(PontoMedido(pontos[2], escolha=escolha))
    return NovaCalibracao(instrumento, data, medidos, laboratorio="Lab Fictício",
                          certificado="CERT-1")


def test_registra_aprovada_com_proxima_data(repo, paquimetro):
    instrumento, pontos = paquimetro
    repo.registrar_calibracao(calibracao(instrumento, pontos), HOJE)
    [salva] = repo.listar_calibracoes(instrumento)
    assert salva.resultado == Resultado.APROVADO
    assert salva.data_proxima == date(2028, 3, 10)


def test_reprovada_quando_a_faixa_com_u_passa(repo, paquimetro):
    instrumento, pontos = paquimetro
    repo.registrar_calibracao(calibracao(instrumento, pontos, valores=(30.0, 60.045)), HOJE)
    assert repo.listar_calibracoes(instrumento)[0].resultado == Resultado.REPROVADO


def test_orientacao_indicativa(repo, paquimetro):
    instrumento, pontos = paquimetro
    repo.registrar_calibracao(
        calibracao(instrumento, pontos, escolha=Resultado.APROVADO_INDICATIVO), HOJE)
    assert repo.listar_calibracoes(instrumento)[0].resultado == Resultado.APROVADO_INDICATIVO


def test_ponto_em_branco_impede_salvar(repo, paquimetro):
    instrumento, pontos = paquimetro
    with pytest.raises(ErroDeValidacao, match="Ponto 2"):
        repo.registrar_calibracao(calibracao(instrumento, pontos, valores=(30.0, None)), HOJE)
    assert repo.listar_calibracoes(instrumento) == []


def test_sem_incerteza_impede_salvar(repo, paquimetro):
    instrumento, pontos = paquimetro
    nova = calibracao(instrumento, pontos)
    nova.pontos[0].incerteza = None
    with pytest.raises(ErroDeValidacao, match="incerteza ausente"):
        repo.registrar_calibracao(nova, HOJE)


def test_nao_aplicavel_exige_motivo_e_nao_conta(repo, paquimetro):
    instrumento, pontos = paquimetro
    nova = calibracao(instrumento, pontos, valores=(30.0, 60.2))  # 2º ponto estaria reprovado
    nova.pontos[1] = PontoMedido(pontos[1], escolha=Resultado.NAO_APLICAVEL)
    with pytest.raises(ErroDeValidacao, match="não se aplica"):
        repo.registrar_calibracao(nova, HOJE)
    nova.pontos[1].observacao = "Bico danificado, ponto não medido"
    repo.registrar_calibracao(nova, HOJE)
    assert repo.listar_calibracoes(instrumento)[0].resultado == Resultado.APROVADO


def test_pontos_faltando_ou_sobrando_sao_recusados(repo, paquimetro):
    instrumento, pontos = paquimetro
    nova = calibracao(instrumento, pontos)
    nova.pontos.pop()
    with pytest.raises(ErroDeValidacao, match="não correspondem ao plano"):
        repo.registrar_calibracao(nova, HOJE)


def test_data_futura_e_instrumento_desativado(repo, paquimetro):
    instrumento, pontos = paquimetro
    with pytest.raises(ErroDeValidacao, match="futuro"):
        repo.registrar_calibracao(calibracao(instrumento, pontos, data=date(2027, 3, 16)), HOJE)
    repo.desativar_instrumento(instrumento, HOJE, "Quebrou", HOJE)
    with pytest.raises(ErroDeValidacao, match="desativado"):
        repo.registrar_calibracao(calibracao(instrumento, pontos), HOJE)


def test_instrumento_sem_plano(repo):
    sem_plano = repo.incluir_instrumento(Instrumento("TRE-999", "Trena"))
    with pytest.raises(ErroDeValidacao, match="sem plano"):
        repo.registrar_calibracao(NovaCalibracao(sem_plano, HOJE, []), HOJE)


def test_foto_do_ponto_nao_muda_quando_o_plano_muda(repo, paquimetro):
    instrumento, pontos = paquimetro
    calibracao_id = repo.registrar_calibracao(calibracao(instrumento, pontos), HOJE)
    plano_id = repo.obter_instrumento(instrumento).plano_id
    ponto = repo.listar_pontos(plano_id)[0]
    ponto.tolerancia_superior = 0.10  # plano corrigido depois
    repo.atualizar_ponto(ponto)
    registrado = repo.pontos_da_calibracao(calibracao_id)[0]
    assert registrado.tolerancia_superior == 0.05
    assert (registrado.valor, registrado.incerteza, registrado.resultado) == (
        30.01, 0.01, Resultado.APROVADO)


def test_ponto_sem_nominal_fixo_usa_o_erro(repo):
    # Durômetro: o laboratório externo entrega o erro; tolerância ± 3,0.
    plano = repo.incluir_plano(Plano("Plano DUR-900"))
    ponto = repo.incluir_ponto(PontoPlano(plano, "NUMERICO", "1º ponto 67 a 80 HR15T",
                                          tolerancia_inferior=-3.0, tolerancia_superior=3.0))
    instrumento = repo.incluir_instrumento(
        Instrumento("DUR-900", "Durômetro", periodicidade_meses=12, plano_id=plano))
    repo.registrar_calibracao(NovaCalibracao(instrumento, HOJE, [
        PontoMedido(ponto, valor=0.8, incerteza=0.33, valor_padrao=75.3, valor_medido=76.1)
    ]), HOJE)
    [registrado] = repo.pontos_da_calibracao(repo.listar_calibracoes(instrumento)[0].id)
    assert (registrado.resultado, registrado.valor_padrao) == (Resultado.APROVADO, 75.3)
