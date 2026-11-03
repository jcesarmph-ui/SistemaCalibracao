"""Caixa "Reserva" da ficha: põe e tira " - Reserva" da localização (pedido de 2026-11-03)."""

import pytest

from calibracao.regras.localizacao import com_reserva, eh_reserva, padronizar_localizacao


@pytest.mark.parametrize("antes, depois", [
    ("Laboratório", "Laboratório - Reserva"),
    ("CT-01", "CT-01 - Reserva"),
    ("Laboratório - Orientação indicativa", "Laboratório - Reserva - Orientação indicativa"),
    ("Laboratório - Reserva", "Laboratório - Reserva"),   # já era: não repete
    ("", "Reserva"),
    (None, "Reserva"),
])
def test_marcar_reserva(antes, depois):
    assert com_reserva(antes, True) == depois
    assert eh_reserva(depois)


@pytest.mark.parametrize("antes, depois", [
    ("Laboratório - Reserva", "Laboratório"),
    ("CT-01 - Reserva", "CT-01"),
    ("Laboratório - Reserva - Orientação indicativa", "Laboratório - Orientação indicativa"),
    ("Reserva Laboratório", "Laboratório"),               # digitado à mão, fora do padrão
    ("Laboratório", "Laboratório"),
    ("Reserva", None),
])
def test_desmarcar_reserva(antes, depois):
    assert com_reserva(antes, False) == depois
    assert not eh_reserva(depois)


def test_reserva_com_indicativa_sobrevive_a_padronizacao():
    """Ao salvar, a localização é padronizada: as duas etiquetas continuam."""
    texto = com_reserva("Laboratório - Orientação indicativa", True)
    assert padronizar_localizacao(texto) == texto


def test_codigo_do_local_com_traco_nao_se_perde():
    assert com_reserva("CT-01 - Reserva", False) == "CT-01"
    assert com_reserva("GL-02", True) == "GL-02 - Reserva"
