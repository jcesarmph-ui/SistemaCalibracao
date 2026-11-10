"""Configuração comum dos testes."""

import pytest


@pytest.fixture(autouse=True)
def nome_novo_confirmado(monkeypatch):
    """A pergunta "Nome novo" (tipo/local que ninguém usa) espera um clique: nos testes ela
    responde "Criar novo" sozinha. Quem quiser testar a resposta muda `respostas`."""
    from calibracao.interface.janela_instrumento import JanelaEditarInstrumento

    perguntas = []

    def responder(self, novos):
        perguntas.append(novos)
        return perguntas_respostas.pop(0) if perguntas_respostas else True

    perguntas_respostas: list[bool] = []
    monkeypatch.setattr(JanelaEditarInstrumento, "confirmar_nomes_novos", responder)
    return perguntas, perguntas_respostas
