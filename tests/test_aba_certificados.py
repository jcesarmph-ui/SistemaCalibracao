"""Tela dos certificados em PDF: escolher na Nova calibração, trocar no EDITAR, abrir pelo
"Ver calibração" e pela aba Certificados. PDFs fictícios, gerados no próprio teste."""

import datetime
import os
from datetime import date
from pathlib import Path

import pytest

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

from PySide6.QtGui import QDesktopServices  # noqa: E402
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
)
from calibracao.interface.aba_certificados import AbaCertificados  # noqa: E402
from calibracao.regras.avaliacao import Resultado  # noqa: E402
from calibracao.regras.condicao import ParecerFinal  # noqa: E402
from calibracao.regras.lixeira import Tipo  # noqa: E402

HOJE = date(2026, 11, 10)
J = JanelaNovaCalibracao


def pdf(pasta: Path, nome: str, texto: str = "certificado") -> Path:
    arquivo = pasta / nome
    arquivo.write_bytes(b"%PDF-1.4\n% " + texto.encode() + b"\n%%EOF\n")
    return arquivo


@pytest.fixture(scope="module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture
def abertos(monkeypatch):
    """Troca o "abrir no Windows" por uma lista, para o teste não abrir nada de verdade."""
    lista = []
    monkeypatch.setattr(QDesktopServices, "openUrl",
                        lambda url: lista.append(Path(url.toLocalFile())) or True)
    return lista


@pytest.fixture
def repo(tmp_path):
    (tmp_path / "dados").mkdir()
    with Repositorio.abrir(tmp_path / "dados" / "calibracao.db", HOJE) as repositorio:
        yield repositorio


@pytest.fixture
def instrumento(repo):
    plano = repo.incluir_plano(Plano("Plano PAQ-902"))
    repo.incluir_ponto(PontoPlano(plano, "VERIFICACAO", "Aspecto geral"))
    instrumento_id = repo.incluir_instrumento(
        Instrumento("PAQ-902", "Paquímetro", periodicidade_meses=12, plano_id=plano))
    return repo.obter_instrumento(instrumento_id)


def calibrar(repo, instrumento, numero="CERT 7/2026"):
    [ponto] = repo.listar_pontos(instrumento.plano_id)
    return repo.registrar_calibracao(NovaCalibracao(
        instrumento.id, date(2026, 11, 3), [PontoMedido(ponto.id, escolha=Resultado.APROVADO)],
        parecer_final=ParecerFinal.APROVADO, certificado=numero), HOJE)


def preencher_e_salvar(janela):
    janela.tabela.cellWidget(0, J.ENCONTRADO).setCurrentText("Aprovado")
    janela.parecer.setCurrentIndex(janela.parecer.findData(ParecerFinal.APROVADO))
    janela.salvar_calibracao()


def test_nova_calibracao_guarda_o_pdf_escolhido(app, repo, instrumento, tmp_path):
    janela = JanelaNovaCalibracao(repo, instrumento, HOJE, usuario="ana - PC-01")
    assert janela.escolher_pdf.text() == "Adicionar certificado (PDF)"
    assert "Nenhum PDF" in janela.nome_pdf.text()
    assert janela.usar_pdf(pdf(tmp_path, "cert do lab.pdf"))
    assert "cert do lab.pdf" in janela.nome_pdf.text()
    janela.certificado.setText("CERT 9/2026")
    preencher_e_salvar(janela)
    assert janela.calibracao_id is not None, janela.avisos.text()
    guardado = repo.certificado_da_calibracao(janela.calibracao_id)
    assert (guardado.nome_original, guardado.enviado_por) == ("cert do lab.pdf", "ana - PC-01")
    assert janela.erro_pdf is None


def test_sem_pdf_continua_salvando(app, repo, instrumento):
    janela = JanelaNovaCalibracao(repo, instrumento, HOJE)
    preencher_e_salvar(janela)
    assert janela.calibracao_id is not None
    assert repo.certificado_da_calibracao(janela.calibracao_id) is None


def test_arquivo_que_nao_e_pdf_e_recusado_na_hora(app, repo, instrumento, tmp_path):
    falso = tmp_path / "foto.pdf"
    falso.write_bytes(b"isto nao e pdf")
    janela = JanelaNovaCalibracao(repo, instrumento, HOJE)
    assert not janela.usar_pdf(falso)
    assert "não é um PDF válido" in janela.avisos.text()
    assert janela.pdf_escolhido is None


def test_pdf_que_sumiu_antes_de_salvar_nao_deixa_salvar(app, repo, instrumento, tmp_path):
    arquivo = pdf(tmp_path, "cert.pdf")
    janela = JanelaNovaCalibracao(repo, instrumento, HOJE)
    janela.usar_pdf(arquivo)
    arquivo.unlink()
    preencher_e_salvar(janela)
    assert janela.calibracao_id is None
    assert "PDF do certificado" in janela.avisos.text()
    assert repo.listar_calibracoes(instrumento.id) == []


def test_editar_so_para_trocar_o_pdf(app, repo, instrumento, tmp_path):
    calibracao_id = calibrar(repo, instrumento)
    repo.anexar_certificado(calibracao_id, pdf(tmp_path, "antigo.pdf", "a"), "ana",
                            datetime.datetime(2026, 11, 10, 9, 0))
    calibracao = repo.obter_calibracao(calibracao_id)
    janela = JanelaNovaCalibracao(repo, instrumento, HOJE, corrigir=calibracao, usuario="bia")
    assert janela.escolher_pdf.text() == "Substituir certificado (PDF)"
    assert "antigo.pdf" in janela.nome_pdf.text()
    janela.usar_pdf(pdf(tmp_path, "novo.pdf", "b"))
    assert "vai para a Lixeira" in janela.nome_pdf.text()
    janela.salvar_calibracao()  # nada mais mudou: só o PDF, e isso não é erro
    assert janela.result() == JanelaNovaCalibracao.Accepted, janela.avisos.text()
    assert janela.mudancas == []
    assert repo.certificado_da_calibracao(calibracao_id).nome_original == "novo.pdf"
    na_lixeira = [item for item in repo.listar_lixeira() if item.tipo == Tipo.CERTIFICADO]
    assert len(na_lixeira) == 1


def test_editar_sem_mudar_nada_continua_avisando(app, repo, instrumento):
    calibracao = repo.obter_calibracao(calibrar(repo, instrumento))
    janela = JanelaNovaCalibracao(repo, instrumento, HOJE, corrigir=calibracao)
    janela.salvar_calibracao()
    assert "Nada foi alterado" in janela.avisos.text()


def test_ver_calibracao_abre_o_pdf(app, repo, instrumento, tmp_path, abertos):
    calibracao_id = calibrar(repo, instrumento)
    calibracao = repo.obter_calibracao(calibracao_id)
    sem_pdf = JanelaVerCalibracao(repo, instrumento, calibracao)
    assert sem_pdf.abrir_pdf.isHidden()
    repo.anexar_certificado(calibracao_id, pdf(tmp_path, "cert.pdf"), "ana",
                            datetime.datetime(2026, 11, 10, 9, 0))
    janela = JanelaVerCalibracao(repo, instrumento, calibracao)
    assert not janela.abrir_pdf.isHidden()
    janela.abrir_o_pdf()
    assert abertos == [repo.caminho_do_certificado(janela.pdf)]
    assert "PDF aberto" in janela.aviso_pdf.text()


def test_aba_lista_pesquisa_e_abre_com_um_clique(app, repo, instrumento, tmp_path, abertos):
    aba = AbaCertificados(repo)
    aba.atualizar()
    assert "Nenhum PDF" in aba.avisos.text()
    for numero, nome in [("CERT 7/2026", "a.pdf"), ("RBC-55", "b.pdf")]:
        repo.anexar_certificado(calibrar(repo, instrumento, numero), pdf(tmp_path, nome, nome),
                                "ana", datetime.datetime.now())
    aba.atualizar()
    assert aba.tabela.rowCount() == 2
    assert [aba.tabela.horizontalHeaderItem(c).text() for c in range(3)] == [
        "Código do instrumento", "Nº do certificado", "Data da calibração"]
    assert aba.tabela.item(0, 0).text() == "PAQ-902"
    assert aba.tabela.item(0, 2).text() == "03/11/2026"
    aba.busca.setText("rbc")
    assert aba.tabela.rowCount() == 1
    assert aba.contagem.text() == "1 de 2"
    aba.abrir_linha(0)
    assert len(abertos) == 1 and abertos[0].read_bytes().endswith(b"b.pdf\n%%EOF\n")
    assert "PDF aberto" in aba.avisos.text()
    # Botão "Abrir certificado" na linha (pedido de 2026-11-10) abre o mesmo PDF.
    botao = aba.tabela.cellWidget(0, 3)
    assert botao is not None and botao.text().strip() == "Abrir certificado"
    botao.click()
    assert len(abertos) == 2 and abertos[1] == abertos[0]


def test_pdf_sumido_ou_mexido_e_avisado(app, repo, instrumento, tmp_path, abertos):
    calibracao_id = calibrar(repo, instrumento)
    repo.anexar_certificado(calibracao_id, pdf(tmp_path, "c.pdf"), "ana",
                            datetime.datetime.now())
    aba = AbaCertificados(repo)
    aba.atualizar()
    caminho = repo.caminho_do_certificado(repo.certificado_da_calibracao(calibracao_id))
    caminho.write_bytes(b"%PDF-1.4\n% mexido\n")
    aba.abrir_linha(0)
    assert "foi alterado depois" in aba.avisos.text() and len(abertos) == 1
    caminho.unlink()
    aba.abrir_linha(0)
    assert "não foi encontrado" in aba.avisos.text() and len(abertos) == 1


def test_painel_avisa_quando_a_calibracao_salvou_mas_o_pdf_nao(app, repo, instrumento,
                                                                tmp_path, monkeypatch):
    painel = PainelCalibracoes(repo, HOJE)
    painel.mostrar(instrumento)

    def falha(*_args, **_kw):
        raise OSError("rede caiu")

    monkeypatch.setattr(repo, "anexar_certificado", falha)
    janela = JanelaNovaCalibracao(repo, instrumento, HOJE)
    janela.usar_pdf(pdf(tmp_path, "cert.pdf"))
    preencher_e_salvar(janela)
    assert janela.calibracao_id is not None  # a calibração ficou salva
    assert "rede caiu" in janela.erro_pdf and "EDITAR" in janela.erro_pdf
