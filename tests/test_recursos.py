"""Logo e ícone embutidos no .exe ou, fora dele, na pasta de dados."""

import sys

from calibracao.interface.recursos import recurso


def test_fora_do_exe_usa_a_pasta_de_dados(tmp_path):
    assert recurso("logo_mg.png", tmp_path) == tmp_path / "logo_mg.png"


def test_no_exe_usa_o_arquivo_embutido(tmp_path, monkeypatch):
    embutidos = tmp_path / "meipass"
    (embutidos / "recursos").mkdir(parents=True)
    (embutidos / "recursos" / "logo_mg.png").write_bytes(b"png")
    monkeypatch.setattr(sys, "_MEIPASS", str(embutidos), raising=False)
    assert recurso("logo_mg.png", tmp_path / "dados") == embutidos / "recursos" / "logo_mg.png"


def test_imagem_do_check_das_caixinhas():
    """Caixinha marcada = contorno com ✓ (pedido de 2026-11-03): o PNG é gerado pelo programa."""
    from pathlib import Path

    from calibracao.interface.estilo import estilo
    from calibracao.interface.marca_check import caminho_do_check, png_do_check

    assert png_do_check().startswith(b"\x89PNG")
    caminho = caminho_do_check()
    assert Path(caminho).read_bytes() == png_do_check()
    assert f"url({caminho})" in estilo()
