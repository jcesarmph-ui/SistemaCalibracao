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


def test_ind_so_quando_reserva_e_indicativa_juntas():
    from calibracao.interface.estilo import abreviar_indicativa, destacar

    juntas = "Laboratório - Reserva - Orientação indicativa"
    assert abreviar_indicativa(juntas)
    html = destacar(juntas)
    assert "IND." in html and "Orientação indicativa" not in html and "Reserva" in html
    # sozinha, continua por extenso
    assert not abreviar_indicativa("Laboratório - Orientação indicativa")
    assert "Orientação indicativa" in destacar("Laboratório - Orientação indicativa")
    assert not abreviar_indicativa("Laboratório - Reserva")


@pytest.mark.parametrize("antes, marcar, depois", [
    ("CT-01", True, "CT-01 - Orientação indicativa"),
    ("Laboratório - Reserva", True, "Laboratório - Reserva - Orientação indicativa"),
    ("CT-01 - Orientação indicativa", False, "CT-01"),
    ("Laboratório - Reserva - Orientação indicativa", False, "Laboratório - Reserva"),
    ("GL-02 (indic.)", False, "GL-02"),          # digitado à mão, fora do padrão
    (None, True, "Orientação indicativa"),
])
def test_marca_de_orientacao_indicativa(antes, marcar, depois):
    from calibracao.regras.localizacao import com_marcas, eh_indicativa

    assert com_marcas(antes, indicativa=marcar) == depois
    assert eh_indicativa(depois) is marcar
