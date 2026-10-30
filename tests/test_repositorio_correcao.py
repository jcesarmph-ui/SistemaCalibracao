"""Repositório: correção de calibração já salva (tudo menos a data, com registro da correção)."""

from datetime import date, datetime

import pytest

from calibracao.dados.repositorio import (
    CorrecaoCalibracao,
    ErroDeValidacao,
    Instrumento,
    NovaCalibracao,
    Plano,
    PontoMedido,
    PontoPlano,
    Repositorio,
)
from calibracao.regras.avaliacao import Resultado
from calibracao.regras.condicao import Condicao, ParecerFinal
from calibracao.regras.lixeira import Tipo

HOJE = date(2027, 3, 15)
AGORA = datetime(2027, 3, 15, 10, 30)


@pytest.fixture
def repo(tmp_path):
    with Repositorio.abrir(tmp_path / "calibracao.db", HOJE) as repositorio:
        yield repositorio


@pytest.fixture
def salva(repo):
    """Paquímetro fictício (2 pontos ± 0,05, U 0,01 + verificação) com uma calibração aprovada."""
    plano = repo.incluir_plano(Plano("Plano PAQ-900"))
    for nominal in (30.0, 60.0):
        repo.incluir_ponto(PontoPlano(plano, "NUMERICO", f"{nominal}", valor_nominal=nominal,
                                      tolerancia_inferior=-0.05, tolerancia_superior=0.05,
                                      incerteza=0.01))
    repo.incluir_ponto(PontoPlano(plano, "VERIFICACAO", "Aspecto geral"))
    instrumento = repo.incluir_instrumento(
        Instrumento("PAQ-900", "Paquímetro", periodicidade_meses=12, plano_id=plano))
    pontos = repo.listar_pontos(plano)
    medidos = [PontoMedido(pontos[0].id, valor=30.01, incerteza=0.01),
               PontoMedido(pontos[1].id, valor=60.02, incerteza=0.01),
               PontoMedido(pontos[2].id, escolha=Resultado.APROVADO)]
    calibracao_id = repo.registrar_calibracao(NovaCalibracao(
        instrumento, date(2027, 3, 10), medidos, parecer_final=ParecerFinal.APROVADO,
        laboratorio="Lab Fictício", certificado="CERT-1"), HOJE)
    return instrumento, calibracao_id


def correcao_igual(repo, calibracao_id, **mudar) -> CorrecaoCalibracao:
    """Correção com tudo como está salvo; `mudar` troca campos da calibração."""
    atual = repo.obter_calibracao(calibracao_id)
    pontos = {r.id: PontoMedido(0, valor=r.valor, incerteza=r.incerteza,
                                escolha=r.resultado if r.tipo == "VERIFICACAO" else None,
                                observacao=r.observacao)
              for r in repo.pontos_da_calibracao(calibracao_id)}
    dados = dict(parecer_final=atual.parecer_final, motivo_parecer=atual.motivo_parecer,
                 laboratorio=atual.laboratorio, certificado=atual.certificado,
                 responsavel=atual.responsavel, custo=atual.custo, observacoes=atual.observacoes)
    dados.update(mudar)
    return CorrecaoCalibracao(pontos, **dados)


def test_corrige_dados_do_certificado_e_guarda_o_registro(repo, salva):
    _, calibracao_id = salva
    mudancas = repo.corrigir_calibracao(
        calibracao_id, correcao_igual(repo, calibracao_id, certificado="CERT-2", custo=150.0),
        "maria.silva", AGORA)
    assert mudancas == ["Certificado: CERT-1 → CERT-2", "Custo (R$): — → 150"]
    corrigida = repo.obter_calibracao(calibracao_id)
    assert (corrigida.certificado, corrigida.custo) == ("CERT-2", 150.0)
    [registro] = repo.listar_correcoes(calibracao_id)
    assert (registro.quando, registro.usuario, registro.mudancas) == (AGORA, "maria.silva",
                                                                       mudancas)


def test_corrigir_valor_reavalia_o_ponto_e_o_resultado(repo, salva):
    instrumento, calibracao_id = salva
    correcao = correcao_igual(repo, calibracao_id,
                              parecer_final=ParecerFinal.ORIENTACAO_INDICATIVA)
    primeiro = repo.pontos_da_calibracao(calibracao_id)[0]
    correcao.pontos[primeiro.id].valor = 30.045  # 0,045 + U 0,01 passa de 0,05
    mudancas = repo.corrigir_calibracao(calibracao_id, correcao, "maria.silva", AGORA)
    assert "Ponto 1 (30.0): valor 30,01 → 30,045; resultado Aprovado → Reprovado" in mudancas
    assert "Resultado: Aprovado → Reprovado" in mudancas
    assert repo.obter_calibracao(calibracao_id).resultado == Resultado.REPROVADO
    assert repo.pontos_da_calibracao(calibracao_id)[0].resultado == Resultado.REPROVADO
    # o parecer mudou a condição do instrumento, na data da calibração
    atual = repo.condicao_atual(instrumento)
    assert (atual.condicao, atual.data) == (Condicao.ORIENTACAO_INDICATIVA, date(2027, 3, 10))


def test_reprovada_nao_pode_ficar_com_parecer_aprovado(repo, salva):
    _, calibracao_id = salva
    correcao = correcao_igual(repo, calibracao_id)
    correcao.pontos[repo.pontos_da_calibracao(calibracao_id)[0].id].valor = 30.045
    with pytest.raises(ErroDeValidacao, match="Aprovado"):
        repo.corrigir_calibracao(calibracao_id, correcao, "maria.silva", AGORA)


def test_ponto_apagado_e_recusado(repo, salva):
    _, calibracao_id = salva
    correcao = correcao_igual(repo, calibracao_id)
    correcao.pontos[repo.pontos_da_calibracao(calibracao_id)[0].id].valor = None
    with pytest.raises(ErroDeValidacao, match="Ponto 1"):
        repo.corrigir_calibracao(calibracao_id, correcao, "maria.silva", AGORA)
    assert repo.listar_correcoes(calibracao_id) == []


def test_sem_mudanca_e_recusado(repo, salva):
    _, calibracao_id = salva
    with pytest.raises(ErroDeValidacao, match="Nada foi alterado"):
        repo.corrigir_calibracao(calibracao_id, correcao_igual(repo, calibracao_id),
                                 "maria.silva", AGORA)


def test_voltar_o_parecer_desfaz_a_mudanca_de_condicao(repo, salva):
    instrumento, calibracao_id = salva
    repo.corrigir_calibracao(calibracao_id, correcao_igual(
        repo, calibracao_id, parecer_final=ParecerFinal.REPROVADO_DESATIVADO,
        motivo_parecer="Bico gasto"), "maria.silva", AGORA)
    assert repo.esta_desativado(instrumento)
    assert repo.condicao_atual(instrumento).motivo == "Bico gasto"
    repo.corrigir_calibracao(calibracao_id, correcao_igual(
        repo, calibracao_id, parecer_final=ParecerFinal.APROVADO, motivo_parecer=None),
        "maria.silva", AGORA)
    assert repo.condicao_atual(instrumento).condicao == Condicao.EM_USO
    assert repo.historico_condicao(instrumento) == []
    assert len(repo.listar_correcoes(calibracao_id)) == 2


def test_parecer_nao_muda_se_a_condicao_mudou_depois(repo, salva):
    instrumento, calibracao_id = salva
    repo.mudar_condicao(instrumento, Condicao.DESATIVADO, date(2027, 3, 12), "Perdido", HOJE)
    with pytest.raises(ErroDeValidacao, match="12/03/2027"):
        repo.corrigir_calibracao(calibracao_id, correcao_igual(
            repo, calibracao_id, parecer_final=ParecerFinal.ORIENTACAO_INDICATIVA),
            "maria.silva", AGORA)
    # o resto ainda pode ser corrigido
    repo.corrigir_calibracao(calibracao_id, correcao_igual(repo, calibracao_id,
                                                           responsavel="João"),
                             "maria.silva", AGORA)


def test_calibracao_na_lixeira_nao_e_corrigida(repo, salva):
    _, calibracao_id = salva
    correcao = correcao_igual(repo, calibracao_id, certificado="CERT-2")
    repo.enviar_para_lixeira(Tipo.CALIBRACAO, calibracao_id, None, AGORA)
    with pytest.raises(ErroDeValidacao, match="Lixeira"):
        repo.corrigir_calibracao(calibracao_id, correcao, "maria.silva", AGORA)


def test_modo_consulta_nao_corrige(repo, salva):
    _, calibracao_id = salva
    repo.modo_consulta = True
    with pytest.raises(ErroDeValidacao):
        repo.corrigir_calibracao(calibracao_id, correcao_igual(repo, calibracao_id,
                                                               certificado="X"),
                                 "maria.silva", AGORA)
