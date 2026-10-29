"""Trava de edição para uso em rede (decisão do usuário em 2026-10-29).

Quem abre o programa primeiro edita; os outros entram em modo consulta. Quem edita manda um
"sinal" (um número que sobe) a cada 30 segundos. A trava vence quando o dono para de dar sinal —
computador desligado ou travado — e aí outra pessoa pode passar para edição.

Para não depender do relógio dos computadores estarem certos, a trava vence de dois jeitos:
- o sinal ficou parado por 2 minutos, contados pelo relógio de QUEM OBSERVA; ou
- a hora do último sinal (gravada por quem editava) tem mais de 10 minutos — folga larga para
  relógios um pouco diferentes; assim, uma trava esquecida de ontem não obriga ninguém a esperar.
"""

import datetime

INTERVALO_SINAL = datetime.timedelta(seconds=30)
SINAL_PARADO = datetime.timedelta(minutes=2)
SINAL_ANTIGO = datetime.timedelta(minutes=10)
# Quem edita e deixa o programa parado (sem mouse nem teclado) por 30 minutos libera a edição
# para os outros — mas só se não houver nada digitado sem salvar (decisão de 2026-10-29).
TEMPO_PARADO = datetime.timedelta(minutes=30)


def sinal_antigo(ultimo_sinal: datetime.datetime, agora: datetime.datetime) -> bool:
    return agora - ultimo_sinal > SINAL_ANTIGO


class ObservadorDeSinal:
    """Acompanha o sinal de quem edita, visto de outro computador."""

    def __init__(self) -> None:
        self._sinal: int | None = None
        self._desde: datetime.datetime | None = None

    def ver(self, sinal: int | None, agora: datetime.datetime) -> None:
        """Registra o sinal lido do banco agora (None = ninguém editando)."""
        if sinal != self._sinal:
            self._sinal, self._desde = sinal, agora

    def parado(self, agora: datetime.datetime) -> bool:
        """O mesmo sinal há 2 minutos ou mais: quem editava parou de responder."""
        return (self._sinal is not None and self._desde is not None
                and agora - self._desde >= SINAL_PARADO)

    @property
    def sinal(self) -> int | None:
        return self._sinal
