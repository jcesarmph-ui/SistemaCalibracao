"""Padronização da localização (pedido do usuário em 2026-10-29)."""

import pytest

from calibracao.regras.localizacao import local_do_filtro, padronizar_localizacao


@pytest.mark.parametrize(
    ("antes", "depois"),
    [
        ("Reserva Laboratório", "Laboratório - Reserva"),
        ("Reserva - Lab", "Laboratório - Reserva"),
        ("Lab. Orientativo", "Laboratório - Orientação indicativa"),
        ("Laboratório (indicativa)", "Laboratório - Orientação indicativa"),
        ("LAB", "Laboratório"),
        ("Laboratório", "Laboratório"),
        ("CT-01 Orientativo", "CT-01 - Orientação indicativa"),
        ("CT-04 (Indicativa)", "CT-04 - Orientação indicativa"),
        ("GL-02 (Orientativo)", "GL-02 - Orientação indicativa"),
        ("Filial 1 - Orientativo", "Filial 1 - Orientação indicativa"),
        ("Embalagem (indic.)", "Embalagem - Orientação indicativa"),
        ("Galpão (indicativo)", "Galpão - Orientação indicativa"),
        ("CT-03 Or. Ind.", "CT-03 - Orientação indicativa"),
        ("Laboratório - Orientação indicativa", "Laboratório - Orientação indicativa"),  # de novo
        ("  CL-01  ", "CL-01"),
        ("Compressor 3", "Compressor 3"),
        ("Recebimento", "Recebimento"),  # não confundir com "Reserva"/"Lab"
        ("", None),
        (None, None),
    ],
)
def test_padronizar_localizacao(antes, depois):
    assert padronizar_localizacao(antes) == depois


def test_local_do_filtro_junta_reserva_e_orientacao_indicativa():
    assert local_do_filtro("CT-01 - Orientação indicativa") == "CT-01"
    assert local_do_filtro("Laboratório - Reserva") == "Laboratório"
    assert local_do_filtro("Laboratório - Orientação indicativa") == "Laboratório"
    assert local_do_filtro("Ponte Rolante") == "Ponte Rolante"
    assert local_do_filtro(None) is None
