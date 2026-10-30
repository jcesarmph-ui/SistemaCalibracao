"""Lançador: cópia do programa para o PC, uma vez por versão."""

from calibracao.lancador import (
    PRONTO,
    copia_pronta,
    copiar_para_o_pc,
    limpar_versoes_antigas,
    versao_da_rede,
)


def programa_na_rede(tmp_path, versao="1.0.0_20261030-150000"):
    programa = tmp_path / "rede" / "programa"
    (programa / "_internal").mkdir(parents=True)
    (programa / "Calibração de Instrumentos.exe").write_bytes(b"exe")
    (programa / "_internal" / "python.dll").write_bytes(b"dll")
    (programa / "versao.txt").write_text(versao + "\n", encoding="utf-8")
    return programa


def test_copia_uma_vez_por_versao(tmp_path):
    programa = programa_na_rede(tmp_path)
    cache = tmp_path / "cache"
    versao = versao_da_rede(programa)
    assert versao == "1.0.0_20261030-150000"
    assert not copia_pronta(cache, versao)
    destino = copiar_para_o_pc(programa, cache, versao)
    assert (destino / "_internal" / "python.dll").read_bytes() == b"dll"
    assert copia_pronta(cache, versao)
    (destino / "Calibração de Instrumentos.exe").write_bytes(b"usada")
    assert copiar_para_o_pc(programa, cache, versao) == destino  # já copiada: não copia de novo
    assert (destino / "Calibração de Instrumentos.exe").read_bytes() == b"usada"


def test_copia_interrompida_e_refeita(tmp_path):
    programa = programa_na_rede(tmp_path)
    cache = tmp_path / "cache"
    pela_metade = cache / "1.0.0_20261030-150000"
    pela_metade.mkdir(parents=True)  # sem o arquivo de "cópia completa"
    destino = copiar_para_o_pc(programa, cache, "1.0.0_20261030-150000")
    assert (destino / PRONTO).is_file()
    assert (destino / "_internal" / "python.dll").is_file()


def test_versao_nova_substitui_a_antiga(tmp_path):
    cache = tmp_path / "cache"
    copiar_para_o_pc(programa_na_rede(tmp_path), cache, "1.0.0_a")
    copiar_para_o_pc(programa_na_rede(tmp_path / "nova", "1.0.1_b"), cache, "1.0.1_b")
    limpar_versoes_antigas(cache, "1.0.1_b")
    assert [p.name for p in cache.iterdir()] == ["1.0.1_b"]
