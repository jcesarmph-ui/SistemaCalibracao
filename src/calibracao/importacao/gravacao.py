"""Grava o resultado da leitura num banco novo (cadastros e planos, sem nenhuma calibração)."""

import datetime
from pathlib import Path

from calibracao.dados.esquema import conectar, criar_tabelas
from calibracao.importacao.leitura import ResultadoLeitura


def gravar_banco(
    resultado: ResultadoLeitura, caminho: Path, origem: str, sha256_origem: str
) -> None:
    """Cria o banco em `caminho`. Nunca sobrescreve: o arquivo não pode existir."""
    if caminho.exists():
        raise FileExistsError(f"O banco {caminho} já existe; não será sobrescrito.")
    caminho.parent.mkdir(parents=True, exist_ok=True)
    conexao = conectar(caminho)
    try:
        with conexao:
            criar_tabelas(conexao)
            conexao.executemany(
                "INSERT INTO metadados (chave, valor) VALUES (?, ?)",
                [
                    ("importado_de", origem),
                    ("importado_sha256", sha256_origem),
                    ("importado_em", datetime.datetime.now().isoformat(timespec="seconds")),
                ],
            )
            for instrumento in resultado.instrumentos:
                plano_id = None
                if instrumento.pontos:
                    plano_id = conexao.execute(
                        "INSERT INTO planos (nome, observacoes) VALUES (?, ?)",
                        (
                            f"Plano {instrumento.codigo}",
                            f"Importado da aba '{instrumento.aba}' da planilha DQ05.",
                        ),
                    ).lastrowid
                    for ordem, ponto in enumerate(instrumento.pontos, start=1):
                        conexao.execute(
                            """INSERT INTO pontos_plano (
                                plano_id, ordem, ordem_original, secao, tipo, descricao,
                                valor_nominal, unidade, tolerancia_inferior, tolerancia_superior,
                                valor_minimo, valor_maximo, classe_exigida, criterio, incerteza
                            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                            (
                                plano_id, ordem, ponto.ordem_original, ponto.secao, ponto.tipo,
                                ponto.descricao, ponto.valor_nominal, ponto.unidade,
                                ponto.tolerancia_inferior, ponto.tolerancia_superior,
                                ponto.valor_minimo, ponto.valor_maximo, ponto.classe_exigida,
                                ponto.criterio, ponto.incerteza,
                            ),
                        )
                conexao.execute(
                    """INSERT INTO instrumentos (
                        codigo, tipo, localizacao, faixa, resolucao, fabricante, data_compra,
                        periodicidade_meses, plano_id
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                    (
                        instrumento.codigo, instrumento.tipo, instrumento.localizacao,
                        instrumento.faixa, instrumento.resolucao, instrumento.fabricante,
                        instrumento.data_compra, instrumento.periodicidade_meses, plano_id,
                    ),
                )
    finally:
        conexao.close()
