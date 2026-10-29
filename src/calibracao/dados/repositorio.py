"""Repositório: o único lugar do programa que lê e grava no banco.

A tela fala só com esta classe; se um dia o SQLite for trocado, só este arquivo muda. Cada operação
é uma transação curta (banco em pasta de rede, às vezes com 2–3 pessoas). As regras de negócio vêm
de `calibracao.regras` — aqui só se guarda e se busca.
"""

import datetime
import sqlite3
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from calibracao.dados.backup import fazer_backup_diario
from calibracao.dados.esquema import conectar, criar_tabelas
from calibracao.regras.lixeira import erros_desativacao


class ErroDeValidacao(Exception):
    """Dados recusados; `mensagens` vão para a área de avisos da tela (em vermelho)."""

    def __init__(self, mensagens: list[str]):
        super().__init__("; ".join(mensagens))
        self.mensagens = mensagens


@dataclass
class Instrumento:
    codigo: str
    tipo: str
    localizacao: str | None = None
    faixa: str | None = None
    resolucao: str | None = None
    fabricante: str | None = None
    data_compra: str | None = None
    periodicidade_meses: int | None = None
    plano_id: int | None = None
    exige_calibracao: bool = True
    observacoes: str | None = None
    id: int | None = None


@dataclass
class Desativacao:
    instrumento_id: int
    data: datetime.date
    motivo: str
    reativado_em: datetime.date | None = None


_CAMPOS_INSTRUMENTO = [c.name for c in fields(Instrumento) if c.name != "id"]

# Desativado = existe desativação sem data de reativação.
_DESATIVADO = """EXISTS (SELECT 1 FROM desativacoes d
                         WHERE d.instrumento_id = instrumentos.id AND d.reativado_em IS NULL)"""


def _data(texto: str | None) -> datetime.date | None:
    return datetime.date.fromisoformat(texto) if texto else None


def _instrumento(linha: sqlite3.Row) -> Instrumento:
    dados = {campo: linha[campo] for campo in ["id", *_CAMPOS_INSTRUMENTO]}
    dados["exige_calibracao"] = bool(dados["exige_calibracao"])
    return Instrumento(**dados)


class Repositorio:
    def __init__(self, conexao: sqlite3.Connection):
        self._conexao = conexao

    @classmethod
    def abrir(cls, caminho: Path, hoje: datetime.date | None = None) -> "Repositorio":
        """Abre (ou cria) o banco. O backup do dia é feito antes de qualquer atualização."""
        if caminho.exists():
            fazer_backup_diario(caminho, hoje or datetime.date.today())
        conexao = conectar(caminho)
        with conexao:
            criar_tabelas(conexao)
        return cls(conexao)

    def fechar(self) -> None:
        self._conexao.close()

    def __enter__(self) -> "Repositorio":
        return self

    def __exit__(self, *_) -> None:
        self.fechar()

    # ---------------------------------------------------------------- instrumentos

    def listar_instrumentos(self, incluir_desativados: bool = False) -> list[Instrumento]:
        """Instrumentos fora da Lixeira, por código."""
        filtro = "" if incluir_desativados else f"AND NOT {_DESATIVADO}"
        linhas = self._conexao.execute(
            f"SELECT * FROM instrumentos WHERE excluido_em IS NULL {filtro} ORDER BY codigo"
        )
        return [_instrumento(linha) for linha in linhas]

    def obter_instrumento(self, instrumento_id: int) -> Instrumento:
        linha = self._conexao.execute(
            "SELECT * FROM instrumentos WHERE id = ?", (instrumento_id,)
        ).fetchone()
        if linha is None:
            raise KeyError(f"Instrumento {instrumento_id} não existe.")
        return _instrumento(linha)

    def _validar_instrumento(self, instrumento: Instrumento) -> None:
        erros = []
        if not (instrumento.codigo or "").strip():
            erros.append("Informe o código do instrumento.")
        if not (instrumento.tipo or "").strip():
            erros.append("Informe o tipo do instrumento.")
        if instrumento.periodicidade_meses is not None and instrumento.periodicidade_meses <= 0:
            erros.append("A periodicidade deve ser um número de meses maior que zero.")
        repetido = self._conexao.execute(
            "SELECT excluido_em FROM instrumentos WHERE codigo = ? AND id IS NOT ?",
            ((instrumento.codigo or "").strip(), instrumento.id),
        ).fetchone()
        if repetido is not None:
            onde = " (está na Lixeira)" if repetido["excluido_em"] else ""
            erros.append(f"Já existe um instrumento com o código {instrumento.codigo}{onde}.")
        if erros:
            raise ErroDeValidacao(erros)

    def incluir_instrumento(self, instrumento: Instrumento) -> int:
        self._validar_instrumento(instrumento)
        dados = asdict(instrumento)
        dados["codigo"] = dados["codigo"].strip()
        with self._conexao:
            cursor = self._conexao.execute(
                f"INSERT INTO instrumentos ({', '.join(_CAMPOS_INSTRUMENTO)}) "
                f"VALUES ({', '.join('?' * len(_CAMPOS_INSTRUMENTO))})",
                [dados[campo] for campo in _CAMPOS_INSTRUMENTO],
            )
        return cursor.lastrowid

    def atualizar_instrumento(self, instrumento: Instrumento) -> None:
        if instrumento.id is None:
            raise ValueError("Instrumento sem id: use incluir_instrumento.")
        self._validar_instrumento(instrumento)
        dados = asdict(instrumento)
        dados["codigo"] = dados["codigo"].strip()
        with self._conexao:
            self._conexao.execute(
                f"UPDATE instrumentos SET {', '.join(f'{c} = ?' for c in _CAMPOS_INSTRUMENTO)} "
                "WHERE id = ?",
                [*(dados[campo] for campo in _CAMPOS_INSTRUMENTO), instrumento.id],
            )

    # ---------------------------------------------------------------- desativação

    def esta_desativado(self, instrumento_id: int) -> bool:
        return self._desativacao_aberta(instrumento_id) is not None

    def _desativacao_aberta(self, instrumento_id: int) -> sqlite3.Row | None:
        return self._conexao.execute(
            "SELECT * FROM desativacoes WHERE instrumento_id = ? AND reativado_em IS NULL",
            (instrumento_id,),
        ).fetchone()

    def desativar_instrumento(self, instrumento_id: int, data: datetime.date | None,
                              motivo: str | None, hoje: datetime.date) -> None:
        erros = erros_desativacao(motivo, data, hoje)
        if self.esta_desativado(instrumento_id):
            erros.append("Este instrumento já está desativado.")
        if erros:
            raise ErroDeValidacao(erros)
        with self._conexao:
            self._conexao.execute(
                "INSERT INTO desativacoes (instrumento_id, data, motivo) VALUES (?, ?, ?)",
                (instrumento_id, data.isoformat(), motivo.strip()),
            )

    def reativar_instrumento(self, instrumento_id: int, data: datetime.date) -> None:
        aberta = self._desativacao_aberta(instrumento_id)
        if aberta is None:
            raise ErroDeValidacao(["Este instrumento não está desativado."])
        if data < _data(aberta["data"]):
            raise ErroDeValidacao(["A reativação não pode ser antes da desativação."])
        with self._conexao:
            self._conexao.execute(
                "UPDATE desativacoes SET reativado_em = ? WHERE id = ?",
                (data.isoformat(), aberta["id"]),
            )

    def listar_desativados(self) -> list[tuple[Instrumento, Desativacao]]:
        """Aba "Desativados": instrumento + desativação em aberto, mais recentes primeiro."""
        linhas = self._conexao.execute(
            """SELECT i.*, d.data AS d_data, d.motivo AS d_motivo
               FROM instrumentos i JOIN desativacoes d ON d.instrumento_id = i.id
               WHERE d.reativado_em IS NULL AND i.excluido_em IS NULL
               ORDER BY d.data DESC, i.codigo"""
        )
        return [
            (_instrumento(linha), Desativacao(linha["id"], _data(linha["d_data"]),
                                               linha["d_motivo"]))
            for linha in linhas
        ]

    def historico_desativacoes(self, instrumento_id: int) -> list[Desativacao]:
        linhas = self._conexao.execute(
            "SELECT * FROM desativacoes WHERE instrumento_id = ? ORDER BY data, id",
            (instrumento_id,),
        )
        return [
            Desativacao(instrumento_id, _data(linha["data"]), linha["motivo"],
                        _data(linha["reativado_em"]))
            for linha in linhas
        ]
