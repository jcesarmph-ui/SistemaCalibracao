"""PDF do certificado de cada calibração (pedido do usuário em 2026-11-10). PDFs fictícios."""

import datetime
from datetime import date
from pathlib import Path

import pytest

from calibracao.dados import certificados as arquivos_pdf
from calibracao.dados.backup import fazer_backup_diario
from calibracao.dados.esquema import VERSAO_ESQUEMA
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
from calibracao.regras.condicao import ParecerFinal
from calibracao.regras.lixeira import Tipo

HOJE = date(2026, 11, 10)
AGORA = datetime.datetime(2026, 11, 10, 15, 30)


def pdf(pasta: Path, nome: str, texto: str = "certificado") -> Path:
    arquivo = pasta / nome
    arquivo.write_bytes(b"%PDF-1.4\n% " + texto.encode() + b"\n%%EOF\n")
    return arquivo


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "dados").mkdir()
    repositorio = Repositorio.abrir(tmp_path / "dados" / "calibracao.db", HOJE)
    plano = repositorio.incluir_plano(Plano("Plano PAQ-901"))
    ponto = repositorio.incluir_ponto(PontoPlano(plano, "VERIFICACAO", "Aspecto geral"))
    instrumento = repositorio.incluir_instrumento(
        Instrumento("PAQ-901", "Paquímetro", periodicidade_meses=12, plano_id=plano))
    repositorio.calibracao = repositorio.registrar_calibracao(NovaCalibracao(
        instrumento, date(2026, 11, 3), [PontoMedido(ponto, escolha=Resultado.APROVADO)],
        parecer_final=ParecerFinal.APROVADO, certificado="CERT 12/2026"), HOJE)
    yield repositorio
    repositorio.fechar()


def test_anexar_copia_confere_e_aparece_na_aba(repo, tmp_path):
    original = pdf(tmp_path, "certificado do laboratório.pdf")
    certificado_id = repo.anexar_certificado(repo.calibracao, original, "ana - PC-01", AGORA)
    guardado = repo.certificado_da_calibracao(repo.calibracao)
    assert guardado.id == certificado_id
    assert guardado.nome_original == "certificado do laboratório.pdf"
    assert guardado.arquivo.startswith("PAQ-901_2026-11-03_CERT-12-2026_")
    caminho = repo.caminho_do_certificado(guardado)
    assert caminho.parent == tmp_path / "dados" / "certificados"
    assert caminho.read_bytes() == original.read_bytes()  # cópia igual ao original
    assert original.exists()  # o arquivo da pessoa continua onde estava
    assert repo.conferir_certificado(guardado) is None
    [linha] = repo.listar_certificados()
    assert (linha.codigo, linha.numero, linha.data_calibracao) == (
        "PAQ-901", "CERT 12/2026", date(2026, 11, 3))


def test_recusa_o_que_nao_e_pdf(repo, tmp_path):
    texto = tmp_path / "planilha.pdf"
    texto.write_text("isto não é PDF")
    with pytest.raises(ErroDeValidacao, match="não é um PDF válido"):
        repo.anexar_certificado(repo.calibracao, texto, None, AGORA)
    outro = tmp_path / "foto.jpg"
    outro.write_bytes(b"%PDF")
    with pytest.raises(ErroDeValidacao, match="Escolha um arquivo PDF"):
        repo.anexar_certificado(repo.calibracao, outro, None, AGORA)
    assert repo.certificado_da_calibracao(repo.calibracao) is None
    assert not list((tmp_path / "dados" / "certificados").glob("*"))  # nada ficou solto


def test_trocar_o_pdf_manda_o_antigo_para_a_lixeira(repo, tmp_path):
    primeiro = repo.anexar_certificado(repo.calibracao, pdf(tmp_path, "a.pdf", "a"), None, AGORA)
    segundo = repo.anexar_certificado(repo.calibracao, pdf(tmp_path, "b.pdf", "b"), None,
                                      AGORA + datetime.timedelta(seconds=1))
    assert repo.certificado_da_calibracao(repo.calibracao).id == segundo
    [item] = [i for i in repo.listar_lixeira() if i.tipo == Tipo.CERTIFICADO]
    assert item.id == primeiro and item.motivo == "Trocado por outro PDF"
    with pytest.raises(ErroDeValidacao, match="já tem outro PDF"):
        repo.restaurar(Tipo.CERTIFICADO, primeiro)
    # excluir de vez apaga o arquivo da pasta
    arquivo = repo.caminho_do_certificado(repo.obter_certificado(primeiro))
    repo.excluir_permanentemente(Tipo.CERTIFICADO, primeiro, "EXCLUIR")
    assert not arquivo.exists()
    assert repo.certificado_da_calibracao(repo.calibracao).id == segundo


def test_calibracao_na_lixeira_tira_o_pdf_da_aba_e_excluir_de_vez_apaga(repo, tmp_path):
    repo.anexar_certificado(repo.calibracao, pdf(tmp_path, "a.pdf"), None, AGORA)
    arquivo = repo.caminho_do_certificado(repo.certificado_da_calibracao(repo.calibracao))
    repo.enviar_para_lixeira(Tipo.CALIBRACAO, repo.calibracao, None, AGORA)
    assert repo.listar_certificados() == []
    repo.restaurar(Tipo.CALIBRACAO, repo.calibracao)
    assert len(repo.listar_certificados()) == 1  # volta junto com a calibração
    repo.enviar_para_lixeira(Tipo.CALIBRACAO, repo.calibracao, None, AGORA)
    repo.excluir_permanentemente(Tipo.CALIBRACAO, repo.calibracao, "EXCLUIR")
    assert not arquivo.exists()


def test_modo_consulta_nao_anexa(repo, tmp_path):
    repo.modo_consulta = True
    with pytest.raises(ErroDeValidacao):
        repo.anexar_certificado(repo.calibracao, pdf(tmp_path, "a.pdf"), None, AGORA)


def test_pdf_mexido_depois_e_detectado(repo, tmp_path):
    repo.anexar_certificado(repo.calibracao, pdf(tmp_path, "a.pdf"), None, AGORA)
    guardado = repo.certificado_da_calibracao(repo.calibracao)
    repo.caminho_do_certificado(guardado).write_bytes(b"%PDF-1.4 alterado")
    assert "alterado" in repo.conferir_certificado(guardado)
    repo.caminho_do_certificado(guardado).unlink()
    assert "não foi encontrado" in repo.conferir_certificado(guardado)


def test_backup_diario_copia_os_pdfs_novos(repo, tmp_path):
    repo.anexar_certificado(repo.calibracao, pdf(tmp_path, "a.pdf"), None, AGORA)
    banco = tmp_path / "dados" / "calibracao.db"
    fazer_backup_diario(banco, date(2026, 11, 11))
    copias = list((tmp_path / "dados" / "backup" / "certificados").glob("*.pdf"))
    assert [c.name for c in copias] == [repo.certificado_da_calibracao(repo.calibracao).arquivo]
    assert arquivos_pdf.espelhar_no_backup(tmp_path / "dados") == 0  # já estava: não copia de novo


def test_versao_do_banco_nao_muda():
    """A tabela nova não muda a versão do esquema: a versão anterior do programa ainda abre."""
    assert VERSAO_ESQUEMA == 9
