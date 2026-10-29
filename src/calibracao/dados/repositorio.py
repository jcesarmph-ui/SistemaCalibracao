"""Repositório: o único lugar do programa que lê e grava no banco.

A tela fala só com esta classe; se um dia o SQLite for trocado, só este arquivo muda. Cada operação
é uma transação curta (banco em pasta de rede, às vezes com 2–3 pessoas). As regras de negócio vêm
de `calibracao.regras` — aqui só se guarda e se busca.
"""

import datetime
import functools
import sqlite3
import uuid
from dataclasses import asdict, dataclass, fields
from pathlib import Path

from calibracao.dados.backup import fazer_backup_diario
from calibracao.dados.esquema import conectar, criar_tabelas
from calibracao.regras.avaliacao import (
    Avaliacao,
    Resultado,
    avaliar_limite,
    avaliar_numerico,
    resultado_geral,
)
from calibracao.regras.condicao import (
    CONDICAO_DO_PARECER,
    Condicao,
    ParecerFinal,
    erros_mudanca_condicao,
    pareceres_permitidos,
)
from calibracao.regras.cronograma import Situacao, proxima_calibracao, situacao
from calibracao.regras.lixeira import Tipo, bloqueio_exclusao_permanente, bloqueio_restaurar
from calibracao.regras.localizacao import padronizar_localizacao
from calibracao.regras.trava import sinal_antigo

MENSAGEM_CONSULTA = ("Modo consulta: outra pessoa está editando. Nada foi salvo.")
MENSAGEM_OCUPADO = ("O banco de dados está ocupado por outro computador. Nada foi salvo: "
                    "tente de novo em alguns segundos.")


class ErroDeValidacao(Exception):
    """Dados recusados; `mensagens` vão para a área de avisos da tela (em vermelho)."""

    def __init__(self, mensagens: list[str]):
        super().__init__("; ".join(mensagens))
        self.mensagens = mensagens


def _escrita(metodo):
    """Toda gravação: recusada no modo consulta; banco ocupado vira aviso na tela."""

    @functools.wraps(metodo)
    def envolto(self, *args, **kwargs):
        if self.modo_consulta:
            raise ErroDeValidacao([MENSAGEM_CONSULTA])
        try:
            return metodo(self, *args, **kwargs)
        except sqlite3.OperationalError as erro:
            if "locked" in str(erro) or "busy" in str(erro):
                raise ErroDeValidacao([MENSAGEM_OCUPADO]) from erro
            raise

    return envolto


@dataclass
class Trava:
    """Quem está editando agora."""

    usuario: str
    computador: str
    desde: datetime.datetime
    ultimo_sinal: datetime.datetime
    sinal: int
    pedido_usuario: str | None = None      # alguém no modo consulta pediu para editar
    pedido_computador: str | None = None
    pedido_em: datetime.datetime | None = None


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
    custo_compra: float | None = None
    responsavel: str | None = None
    id: int | None = None


@dataclass
class MudancaCondicao:
    """Uma linha do histórico de condição; `calibracao_id` preenchido = veio do parecer final."""

    condicao: Condicao
    data: datetime.date | None
    motivo: str | None = None
    calibracao_id: int | None = None


@dataclass
class Plano:
    nome: str
    observacoes: str | None = None
    id: int | None = None


TIPOS_PONTO = ("NUMERICO", "LIMITE", "CLASSE", "CRITERIO", "VERIFICACAO")


@dataclass
class PontoPlano:
    plano_id: int
    tipo: str
    descricao: str
    ordem: int | None = None  # None = vai para o fim do plano
    secao: str | None = None
    ordem_original: str | None = None
    valor_nominal: float | None = None
    unidade: str | None = None
    tolerancia_inferior: float | None = None
    tolerancia_superior: float | None = None
    valor_minimo: float | None = None
    valor_maximo: float | None = None
    classe_exigida: str | None = None
    criterio: str | None = None
    incerteza: float | None = None
    id: int | None = None


@dataclass
class PontoMedido:
    """O que o usuário preenche em cada ponto ao registrar a calibração.

    Numérico/limite: `valor` (medido, ou o erro do certificado se o ponto não tem nominal fixo) e a
    `incerteza` do certificado — a tela já traz a U do plano preenchida. Classe/critério/
    verificação: `escolha` (aprovado ou reprovado). Qualquer ponto pode ser
    `NAO_APLICAVEL`, com o motivo em `observacao`.
    """

    ponto_plano_id: int
    valor: float | None = None
    incerteza: float | None = None
    escolha: Resultado | None = None
    valor_padrao: float | None = None  # só registro
    valor_medido: float | None = None  # só registro
    observacao: str | None = None


@dataclass
class NovaCalibracao:
    instrumento_id: int
    data_calibracao: datetime.date
    pontos: list[PontoMedido]
    # Escolhido por quem analisa; muda a condição do instrumento (ver regras/condicao.py).
    parecer_final: ParecerFinal | None = None
    motivo_parecer: str | None = None
    laboratorio: str | None = None
    certificado: str | None = None
    responsavel: str | None = None
    custo: float | None = None
    observacoes: str | None = None


@dataclass
class Calibracao:
    id: int
    instrumento_id: int
    data_calibracao: datetime.date
    data_proxima: datetime.date | None
    resultado: Resultado
    laboratorio: str | None
    certificado: str | None
    responsavel: str | None
    observacoes: str | None
    parecer_final: ParecerFinal | None
    motivo_parecer: str | None
    custo: float | None


@dataclass
class PontoRegistrado:
    """A "foto" do ponto guardada com a calibração, mais o que foi medido."""

    ordem: int
    secao: str | None
    tipo: str
    descricao: str
    valor_nominal: float | None
    unidade: str | None
    tolerancia_inferior: float | None
    tolerancia_superior: float | None
    valor_minimo: float | None
    valor_maximo: float | None
    classe_exigida: str | None
    criterio: str | None
    valor: float | None
    incerteza: float | None
    valor_padrao: float | None
    valor_medido: float | None
    resultado: Resultado
    observacao: str | None


@dataclass
class MedicaoTendencia:
    """Um ponto numérico de uma calibração, para o gráfico de tendência.

    `erro` = medido − nominal (ou o erro digitado, se o ponto não tem nominal fixo); a tolerância
    é a da "foto" guardada com a calibração.
    """

    data: datetime.date
    erro: float
    incerteza: float | None
    tolerancia_inferior: float | None
    tolerancia_superior: float | None
    resultado: Resultado


@dataclass
class SerieTendencia:
    """Histórico de um ponto do plano ao longo das calibrações."""

    nome: str
    unidade: str | None
    medicoes: list[MedicaoTendencia]


@dataclass
class LinhaCronograma:
    instrumento: Instrumento
    ultima: datetime.date | None
    proxima: datetime.date | None
    situacao: Situacao
    condicao: Condicao
    parecer_ultima: ParecerFinal | None


@dataclass
class ItemLixeira:
    tipo: Tipo
    id: int
    descricao: str
    excluido_em: str
    motivo: str | None


# Tabela de cada tipo e, quando há, a coluna que aponta para o "pai".
_TABELA = {Tipo.INSTRUMENTO: "instrumentos", Tipo.PLANO: "planos",
           Tipo.PONTO: "pontos_plano", Tipo.CALIBRACAO: "calibracoes"}
_COLUNA_PAI = {Tipo.INSTRUMENTO: "plano_id", Tipo.PONTO: "plano_id",
               Tipo.CALIBRACAO: "instrumento_id"}

ESCOLHAS_QUALITATIVAS = (Resultado.APROVADO, Resultado.REPROVADO)

_CAMPOS_INSTRUMENTO = [c.name for c in fields(Instrumento) if c.name != "id"]
_CAMPOS_PONTO = [c.name for c in fields(PontoPlano) if c.name != "id"]
_CAMPOS_REGISTRADO = [c.name for c in fields(PontoRegistrado)]

# Mudanças de condição que valem: as manuais e as de calibrações fora da Lixeira.
_CONDICOES_VALIDAS = """
    SELECT k.* FROM condicoes k LEFT JOIN calibracoes c ON c.id = k.calibracao_id
    WHERE k.calibracao_id IS NULL OR c.excluido_em IS NULL"""

# Condição atual = mudança válida mais recente; sem nenhuma, "Em uso".
_CONDICAO_ATUAL = f"""COALESCE((SELECT v.condicao FROM ({_CONDICOES_VALIDAS}) v
    WHERE v.instrumento_id = instrumentos.id ORDER BY v.data DESC, v.id DESC LIMIT 1), 'Em uso')"""


def _data(texto: str | None) -> datetime.date | None:
    return datetime.date.fromisoformat(texto) if texto else None


def _mudanca(linha: sqlite3.Row) -> MudancaCondicao:
    return MudancaCondicao(Condicao(linha["condicao"]), _data(linha["data"]), linha["motivo"],
                           linha["calibracao_id"])


def _instrumento(linha: sqlite3.Row) -> Instrumento:
    dados = {campo: linha[campo] for campo in ["id", *_CAMPOS_INSTRUMENTO]}
    dados["exige_calibracao"] = bool(dados["exige_calibracao"])
    return Instrumento(**dados)


class Repositorio:
    def __init__(self, conexao: sqlite3.Connection):
        self._conexao = conexao
        self.token = uuid.uuid4().hex  # identifica esta janela aberta na trava de edição
        # Sem trava (testes, fotos), pode editar; a janela liga o modo consulta se precisar.
        self.modo_consulta = False

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

    # ---------------------------------------------------------------- trava de edição

    def obter_trava(self) -> Trava | None:
        linha = self._conexao.execute("SELECT * FROM trava_edicao WHERE id = 1").fetchone()
        if linha is None:
            return None
        return Trava(linha["usuario"], linha["computador"],
                     datetime.datetime.fromisoformat(linha["desde"]),
                     datetime.datetime.fromisoformat(linha["ultimo_sinal"]), linha["sinal"],
                     linha["pedido_usuario"], linha["pedido_computador"],
                     datetime.datetime.fromisoformat(linha["pedido_em"])
                     if linha["pedido_em"] else None)

    def pedir_edicao(self, usuario: str, computador: str, agora: datetime.datetime) -> bool:
        """Modo consulta: pede para quem edita liberar. False se ninguém estiver editando."""
        try:
            with self._conexao:
                return bool(self._conexao.execute(
                    "UPDATE trava_edicao SET pedido_usuario = ?, pedido_computador = ?, "
                    "pedido_em = ? WHERE id = 1",
                    (usuario, computador, agora.isoformat(timespec="seconds")),
                ).rowcount)
        except sqlite3.OperationalError as erro:
            raise ErroDeValidacao([MENSAGEM_OCUPADO]) from erro

    def recusar_pedido(self) -> None:
        """Quem edita escolheu continuar editando: apaga o pedido."""
        try:
            with self._conexao:
                self._conexao.execute(
                    "UPDATE trava_edicao SET pedido_usuario = NULL, pedido_computador = NULL, "
                    "pedido_em = NULL WHERE token = ?", (self.token,))
        except sqlite3.OperationalError:
            pass  # o pedido continua lá; quem pediu só não recebe a resposta agora

    def tentar_editar(self, usuario: str, computador: str, agora: datetime.datetime,
                      assumir_sinal: int | None = None) -> Trava | None:
        """Pega a trava se estiver livre (ou vencida). Devolve None se pegou; senão, quem tem.

        `assumir_sinal`: o sinal que este computador viu parado por 2 minutos — só toma a trava
        se ela ainda estiver com esse mesmo sinal (ninguém voltou a dar sinal nem pegou antes).
        """
        try:
            with self._conexao:
                self._conexao.execute("BEGIN IMMEDIATE")  # duas pessoas não pegam ao mesmo tempo
                linha = self._conexao.execute(
                    "SELECT * FROM trava_edicao WHERE id = 1").fetchone()
                livre = (
                    linha is None
                    or linha["token"] == self.token
                    # mesma pessoa no mesmo computador: o programa anterior fechou sem liberar
                    or (linha["usuario"], linha["computador"]) == (usuario, computador)
                    or sinal_antigo(datetime.datetime.fromisoformat(linha["ultimo_sinal"]),
                                    agora)
                    or (assumir_sinal is not None and linha["sinal"] == assumir_sinal)
                )
                if livre:
                    self._conexao.execute(
                        """INSERT OR REPLACE INTO trava_edicao
                           (id, token, usuario, computador, desde, ultimo_sinal, sinal)
                           VALUES (1, ?, ?, ?, ?, ?, ?)""",
                        (self.token, usuario, computador,
                         agora.isoformat(timespec="seconds"),
                         agora.isoformat(timespec="seconds"),
                         (linha["sinal"] + 1) if linha else 1),
                    )
        except sqlite3.OperationalError as erro:
            raise ErroDeValidacao([MENSAGEM_OCUPADO]) from erro
        self.modo_consulta = not livre
        return None if livre else self.obter_trava()

    def dar_sinal(self, agora: datetime.datetime) -> bool:
        """Avisa que esta janela continua editando. False = perdeu a trava (vira consulta)."""
        try:
            with self._conexao:
                atualizadas = self._conexao.execute(
                    "UPDATE trava_edicao SET sinal = sinal + 1, ultimo_sinal = ? "
                    "WHERE id = 1 AND token = ?",
                    (agora.isoformat(timespec="seconds"), self.token),
                ).rowcount
        except sqlite3.OperationalError:
            return True  # banco ocupado neste instante: tenta de novo no próximo sinal
        if not atualizadas:
            self.modo_consulta = True
        return bool(atualizadas)

    def liberar_trava(self) -> None:
        """Ao fechar o programa: libera para outra pessoa editar."""
        try:
            with self._conexao:
                self._conexao.execute("DELETE FROM trava_edicao WHERE token = ?", (self.token,))
        except sqlite3.OperationalError:
            pass  # se não der agora, a trava vence sozinha (sinal parado)

    # ---------------------------------------------------------------- instrumentos

    def listar_instrumentos(self, incluir_desativados: bool = False) -> list[Instrumento]:
        """Instrumentos fora da Lixeira, por código."""
        filtro = "" if incluir_desativados else f"AND {_CONDICAO_ATUAL} != 'Desativado'"
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
        if instrumento.custo_compra is not None and instrumento.custo_compra < 0:
            erros.append("O custo de compra não pode ser negativo.")
        repetido = self._conexao.execute(
            "SELECT excluido_em FROM instrumentos WHERE codigo = ? AND id IS NOT ?",
            ((instrumento.codigo or "").strip(), instrumento.id),
        ).fetchone()
        if repetido is not None:
            onde = " (está na Lixeira)" if repetido["excluido_em"] else ""
            erros.append(f"Já existe um instrumento com o código {instrumento.codigo}{onde}.")
        if erros:
            raise ErroDeValidacao(erros)

    @_escrita
    def incluir_instrumento(self, instrumento: Instrumento) -> int:
        self._validar_instrumento(instrumento)
        dados = asdict(instrumento)
        dados["codigo"] = dados["codigo"].strip()
        dados["localizacao"] = padronizar_localizacao(dados["localizacao"])
        with self._conexao:
            cursor = self._conexao.execute(
                f"INSERT INTO instrumentos ({', '.join(_CAMPOS_INSTRUMENTO)}) "
                f"VALUES ({', '.join('?' * len(_CAMPOS_INSTRUMENTO))})",
                [dados[campo] for campo in _CAMPOS_INSTRUMENTO],
            )
        return cursor.lastrowid

    @_escrita
    def atualizar_instrumento(self, instrumento: Instrumento) -> None:
        if instrumento.id is None:
            raise ValueError("Instrumento sem id: use incluir_instrumento.")
        self._validar_instrumento(instrumento)
        dados = asdict(instrumento)
        dados["codigo"] = dados["codigo"].strip()
        dados["localizacao"] = padronizar_localizacao(dados["localizacao"])
        with self._conexao:
            self._conexao.execute(
                f"UPDATE instrumentos SET {', '.join(f'{c} = ?' for c in _CAMPOS_INSTRUMENTO)} "
                "WHERE id = ?",
                [*(dados[campo] for campo in _CAMPOS_INSTRUMENTO), instrumento.id],
            )

    # ---------------------------------------------------------------- condição

    def historico_condicao(self, instrumento_id: int) -> list[MudancaCondicao]:
        """Mudanças de condição que valem, da mais antiga para a mais recente."""
        linhas = self._conexao.execute(
            f"SELECT * FROM ({_CONDICOES_VALIDAS}) WHERE instrumento_id = ? ORDER BY data, id",
            (instrumento_id,),
        )
        return [_mudanca(linha) for linha in linhas]

    def condicao_atual(self, instrumento_id: int) -> MudancaCondicao:
        """Condição de agora; sem histórico, "Em uso" sem data."""
        historico = self.historico_condicao(instrumento_id)
        return historico[-1] if historico else MudancaCondicao(Condicao.EM_USO, None)

    def condicoes_atuais(self) -> dict[int, MudancaCondicao]:
        """Condição de agora dos instrumentos que já tiveram alguma mudança, por id."""
        linhas = self._conexao.execute(f"{_CONDICOES_VALIDAS} ORDER BY k.data, k.id")
        return {linha["instrumento_id"]: _mudanca(linha) for linha in linhas}

    def esta_desativado(self, instrumento_id: int) -> bool:
        return self.condicao_atual(instrumento_id).condicao == Condicao.DESATIVADO

    @_escrita
    def mudar_condicao(self, instrumento_id: int, condicao: Condicao,
                       data: datetime.date | None, motivo: str | None,
                       hoje: datetime.date) -> None:
        """Mudança manual (desativar, reativar, orientação indicativa); motivo é opcional."""
        erros = erros_mudanca_condicao(data, hoje)
        atual = self.condicao_atual(instrumento_id)
        if atual.condicao == condicao:
            erros.append(f'O instrumento já está na condição "{condicao}".')
        if data is not None and atual.data is not None and data < atual.data:
            erros.append("A data não pode ser antes da última mudança de condição "
                         f"({atual.data:%d/%m/%Y}).")
        if erros:
            raise ErroDeValidacao(erros)
        with self._conexao:
            self._inserir_condicao(instrumento_id, condicao, data, motivo, None)

    def _inserir_condicao(self, instrumento_id: int, condicao: Condicao, data: datetime.date,
                          motivo: str | None, calibracao_id: int | None) -> None:
        self._conexao.execute(
            "INSERT INTO condicoes (instrumento_id, condicao, data, motivo, calibracao_id) "
            "VALUES (?, ?, ?, ?, ?)",
            (instrumento_id, str(condicao), data.isoformat(), (motivo or "").strip() or None,
             calibracao_id),
        )

    def desativar_instrumento(self, instrumento_id: int, data: datetime.date | None,
                              motivo: str | None, hoje: datetime.date) -> None:
        self.mudar_condicao(instrumento_id, Condicao.DESATIVADO, data, motivo, hoje)

    def reativar_instrumento(self, instrumento_id: int, data: datetime.date | None,
                             motivo: str | None, hoje: datetime.date) -> None:
        if not self.esta_desativado(instrumento_id):
            raise ErroDeValidacao(["Este instrumento não está desativado."])
        self.mudar_condicao(instrumento_id, Condicao.EM_USO, data, motivo, hoje)

    # ---------------------------------------------------------------- planos e pontos

    def listar_planos(self) -> list[Plano]:
        linhas = self._conexao.execute(
            "SELECT id, nome, observacoes FROM planos WHERE excluido_em IS NULL ORDER BY nome"
        )
        return [Plano(linha["nome"], linha["observacoes"], linha["id"]) for linha in linhas]

    def obter_plano(self, plano_id: int) -> Plano:
        linha = self._conexao.execute(
            "SELECT id, nome, observacoes FROM planos WHERE id = ?", (plano_id,)
        ).fetchone()
        if linha is None:
            raise KeyError(f"Plano {plano_id} não existe.")
        return Plano(linha["nome"], linha["observacoes"], linha["id"])

    @_escrita
    def incluir_plano(self, plano: Plano) -> int:
        if not (plano.nome or "").strip():
            raise ErroDeValidacao(["Informe o nome do plano."])
        with self._conexao:
            cursor = self._conexao.execute(
                "INSERT INTO planos (nome, observacoes) VALUES (?, ?)",
                (plano.nome.strip(), plano.observacoes),
            )
        return cursor.lastrowid

    @_escrita
    def atualizar_plano(self, plano: Plano) -> None:
        if not (plano.nome or "").strip():
            raise ErroDeValidacao(["Informe o nome do plano."])
        with self._conexao:
            self._conexao.execute(
                "UPDATE planos SET nome = ?, observacoes = ? WHERE id = ?",
                (plano.nome.strip(), plano.observacoes, plano.id),
            )

    def listar_pontos(self, plano_id: int) -> list[PontoPlano]:
        """Pontos do plano fora da Lixeira, na ordem."""
        linhas = self._conexao.execute(
            "SELECT * FROM pontos_plano WHERE plano_id = ? AND excluido_em IS NULL "
            "ORDER BY ordem, id",
            (plano_id,),
        )
        return [PontoPlano(**{c: linha[c] for c in [*_CAMPOS_PONTO, "id"]}) for linha in linhas]

    @staticmethod
    def _validar_ponto(ponto: PontoPlano) -> None:
        # Só o que impede o ponto de existir; tolerância ou U em branco são permitidas
        # (o ponto fica "não avaliado" na calibração até alguém preencher).
        erros = []
        if ponto.tipo not in TIPOS_PONTO:
            erros.append(f"Tipo de ponto inválido: {ponto.tipo}.")
        if not (ponto.descricao or "").strip():
            erros.append("Informe a descrição do ponto.")
        pares = [
            (ponto.tolerancia_inferior, ponto.tolerancia_superior, "A tolerância inferior"),
            (ponto.valor_minimo, ponto.valor_maximo, "O valor mínimo"),
        ]
        for menor, maior, nome in pares:
            if menor is not None and maior is not None and menor > maior:
                erros.append(f"{nome} não pode ser maior que a superior/máxima.")
        if erros:
            raise ErroDeValidacao(erros)

    @_escrita
    def incluir_ponto(self, ponto: PontoPlano) -> int:
        self._validar_ponto(ponto)
        dados = asdict(ponto)
        with self._conexao:
            if dados["ordem"] is None:
                dados["ordem"] = self._conexao.execute(
                    "SELECT COALESCE(MAX(ordem), 0) + 1 FROM pontos_plano WHERE plano_id = ?",
                    (ponto.plano_id,),
                ).fetchone()[0]
            cursor = self._conexao.execute(
                f"INSERT INTO pontos_plano ({', '.join(_CAMPOS_PONTO)}) "
                f"VALUES ({', '.join('?' * len(_CAMPOS_PONTO))})",
                [dados[campo] for campo in _CAMPOS_PONTO],
            )
        return cursor.lastrowid

    @_escrita
    def atualizar_ponto(self, ponto: PontoPlano) -> None:
        """Muda o plano daqui para a frente; calibrações já feitas guardam a "foto" antiga."""
        self._validar_ponto(ponto)
        dados = asdict(ponto)
        with self._conexao:
            self._conexao.execute(
                f"UPDATE pontos_plano SET {', '.join(f'{c} = ?' for c in _CAMPOS_PONTO)} "
                "WHERE id = ?",
                [*(dados[campo] for campo in _CAMPOS_PONTO), ponto.id],
            )

    # ---------------------------------------------------------------- calibrações

    @staticmethod
    def avaliar_ponto(ponto: PontoPlano, medido: PontoMedido) -> Avaliacao:
        """Resultado de um ponto (a tela usa para mostrar a cor enquanto o usuário digita)."""
        if medido.escolha == Resultado.NAO_APLICAVEL:
            if not (medido.observacao or "").strip():
                return Avaliacao(Resultado.NAO_INFORMADO, "informe por que não se aplica")
            return Avaliacao(Resultado.NAO_APLICAVEL)
        if ponto.tipo == "NUMERICO":
            return avaliar_numerico(
                medido.valor, nominal=ponto.valor_nominal,
                tolerancia_inferior=ponto.tolerancia_inferior,
                tolerancia_superior=ponto.tolerancia_superior, incerteza=medido.incerteza,
            )
        if ponto.tipo == "LIMITE":
            return avaliar_limite(medido.valor, minimo=ponto.valor_minimo,
                                  maximo=ponto.valor_maximo, incerteza=medido.incerteza)
        if medido.escolha in ESCOLHAS_QUALITATIVAS:
            return Avaliacao(medido.escolha)
        return Avaliacao(Resultado.NAO_INFORMADO)

    @_escrita
    def registrar_calibracao(self, nova: NovaCalibracao, hoje: datetime.date) -> int:
        """Salva a calibração; recusa (ErroDeValidacao) se faltar algo ou houver pendência."""
        instrumento = self.obter_instrumento(nova.instrumento_id)
        erros = []
        if self.na_lixeira(Tipo.INSTRUMENTO, instrumento.id):
            raise ErroDeValidacao(["Instrumento na Lixeira: restaure-o antes."])
        if instrumento.plano_id is not None and self.na_lixeira(Tipo.PLANO, instrumento.plano_id):
            raise ErroDeValidacao(["O plano deste instrumento está na Lixeira: restaure-o antes."])
        if self.esta_desativado(instrumento.id):
            erros.append("Instrumento desativado: reative-o antes de registrar a calibração.")
        if nova.data_calibracao > hoje:
            erros.append("A data da calibração não pode ser no futuro.")
        if nova.custo is not None and nova.custo < 0:
            erros.append("O custo da calibração não pode ser negativo.")
        if instrumento.plano_id is None:
            raise ErroDeValidacao([*erros, "Instrumento sem plano de calibração."])
        pontos = self.listar_pontos(instrumento.plano_id)
        medidos = {m.ponto_plano_id: m for m in nova.pontos}
        if set(medidos) != {p.id for p in pontos}:
            erros.append("Os pontos informados não correspondem ao plano atual do instrumento.")
            raise ErroDeValidacao(erros)

        avaliacoes = [(p, medidos[p.id], self.avaliar_ponto(p, medidos[p.id])) for p in pontos]
        for ponto, _, avaliacao in avaliacoes:
            if avaliacao.resultado in (Resultado.NAO_INFORMADO, Resultado.NAO_AVALIADO):
                motivo = avaliacao.motivo or "não preenchido"
                erros.append(f"Ponto {ponto.ordem} ({ponto.descricao}): {motivo}.")
        if erros:
            raise ErroDeValidacao(erros)

        geral = resultado_geral([a.resultado for _, _, a in avaliacoes])
        if nova.parecer_final is None:
            raise ErroDeValidacao(["Escolha o parecer final da calibração."])
        if nova.parecer_final not in pareceres_permitidos(geral):
            raise ErroDeValidacao(
                ['Calibração reprovada pelos pontos não pode ter parecer final "Aprovado".'])
        nova_condicao = CONDICAO_DO_PARECER[nova.parecer_final]
        atual = self.condicao_atual(instrumento.id)
        if (nova_condicao != atual.condicao and atual.data is not None
                and nova.data_calibracao < atual.data):
            raise ErroDeValidacao(["A data da calibração não pode ser antes da última mudança "
                                   f"de condição ({atual.data:%d/%m/%Y})."])
        proxima = proxima_calibracao(nova.data_calibracao, instrumento.periodicidade_meses)
        with self._conexao:
            calibracao_id = self._conexao.execute(
                """INSERT INTO calibracoes (instrumento_id, data_calibracao, periodicidade_meses,
                       data_proxima, laboratorio, certificado, responsavel, resultado,
                       parecer_final, motivo_parecer, custo_calibracao, observacoes)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (instrumento.id, nova.data_calibracao.isoformat(),
                 instrumento.periodicidade_meses, proxima.isoformat() if proxima else None,
                 nova.laboratorio, nova.certificado, nova.responsavel, str(geral),
                 str(nova.parecer_final), (nova.motivo_parecer or "").strip() or None,
                 nova.custo, nova.observacoes),
            ).lastrowid
            # O parecer só entra no histórico de condição quando muda a condição.
            if nova_condicao != atual.condicao:
                self._inserir_condicao(instrumento.id, nova_condicao, nova.data_calibracao,
                                       nova.motivo_parecer, calibracao_id)
            for ponto, medido, avaliacao in avaliacoes:
                foto = {c: getattr(ponto, c) for c in _CAMPOS_REGISTRADO if hasattr(ponto, c)}
                foto.update(valor=medido.valor, incerteza=medido.incerteza,
                            valor_padrao=medido.valor_padrao, valor_medido=medido.valor_medido,
                            resultado=str(avaliacao.resultado), observacao=medido.observacao)
                self._conexao.execute(
                    f"INSERT INTO pontos_calibracao (calibracao_id, ponto_plano_id, "
                    f"{', '.join(_CAMPOS_REGISTRADO)}) "
                    f"VALUES (?, ?, {', '.join('?' * len(_CAMPOS_REGISTRADO))})",
                    [calibracao_id, ponto.id, *(foto[c] for c in _CAMPOS_REGISTRADO)],
                )
        return calibracao_id

    @staticmethod
    def _calibracao(linha: sqlite3.Row) -> Calibracao:
        return Calibracao(
            linha["id"], linha["instrumento_id"], _data(linha["data_calibracao"]),
            _data(linha["data_proxima"]), Resultado(linha["resultado"]), linha["laboratorio"],
            linha["certificado"], linha["responsavel"], linha["observacoes"],
            ParecerFinal(linha["parecer_final"]) if linha["parecer_final"] else None,
            linha["motivo_parecer"], linha["custo_calibracao"],
        )

    def contar_calibracoes(self) -> int:
        """Calibrações fora da Lixeira, de instrumentos fora da Lixeira (indicador da tela)."""
        return self._conexao.execute(
            """SELECT COUNT(*) FROM calibracoes c JOIN instrumentos i ON i.id = c.instrumento_id
               WHERE c.excluido_em IS NULL AND i.excluido_em IS NULL"""
        ).fetchone()[0]

    def listar_calibracoes(self, instrumento_id: int) -> list[Calibracao]:
        """Calibrações fora da Lixeira, da mais antiga para a mais recente."""
        linhas = self._conexao.execute(
            "SELECT * FROM calibracoes WHERE instrumento_id = ? AND excluido_em IS NULL "
            "ORDER BY data_calibracao, id",
            (instrumento_id,),
        )
        return [self._calibracao(linha) for linha in linhas]

    def pontos_da_calibracao(self, calibracao_id: int) -> list[PontoRegistrado]:
        linhas = self._conexao.execute(
            "SELECT * FROM pontos_calibracao WHERE calibracao_id = ? ORDER BY ordem, id",
            (calibracao_id,),
        )
        return [
            PontoRegistrado(**{c: linha[c] for c in _CAMPOS_REGISTRADO}
                            | {"resultado": Resultado(linha["resultado"])})
            for linha in linhas
        ]

    def tendencia(self, instrumento_id: int) -> list[SerieTendencia]:
        """Pontos numéricos medidos nas calibrações fora da Lixeira, um grupo por ponto do plano.

        Ponto marcado "não aplicável" fica de fora. O nome do grupo vem da calibração mais recente
        (se a descrição do ponto mudou no plano, vale a atual).
        """
        linhas = self._conexao.execute(
            """SELECT c.data_calibracao, p.*
               FROM pontos_calibracao p JOIN calibracoes c ON c.id = p.calibracao_id
               WHERE c.instrumento_id = ? AND c.excluido_em IS NULL AND p.tipo = 'NUMERICO'
                 AND p.valor IS NOT NULL AND p.resultado != ?
               ORDER BY c.data_calibracao, c.id, p.ordem""",
            (instrumento_id, str(Resultado.NAO_APLICAVEL)),
        ).fetchall()
        series: dict[object, SerieTendencia] = {}
        for linha in linhas:
            chave = linha["ponto_plano_id"] or (linha["secao"], linha["descricao"])
            nome = " — ".join(t for t in (linha["secao"], linha["descricao"]) if t)
            serie = series.setdefault(chave, SerieTendencia(nome, linha["unidade"], []))
            serie.nome, serie.unidade = nome, linha["unidade"]
            nominal = linha["valor_nominal"]
            serie.medicoes.append(MedicaoTendencia(
                _data(linha["data_calibracao"]),
                linha["valor"] - nominal if nominal is not None else linha["valor"],
                abs(linha["incerteza"]) if linha["incerteza"] is not None else None,
                linha["tolerancia_inferior"], linha["tolerancia_superior"],
                Resultado(linha["resultado"]),
            ))
        return list(series.values())

    # ---------------------------------------------------------------- cronograma

    def cronograma(self, hoje: datetime.date) -> list[LinhaCronograma]:
        """Instrumentos não desativados que exigem calibração, com a situação de cada um.

        Orientação indicativa continua no cronograma (o instrumento segue calibrado).

        Vale a última calibração fora da Lixeira. A próxima data é a guardada com ela (calculada
        com a periodicidade do cadastro só se a calibração não tiver uma).
        """
        linhas = []
        condicoes = self.condicoes_atuais()
        for instrumento in self.listar_instrumentos():
            if not instrumento.exige_calibracao:
                continue
            calibracoes = self.listar_calibracoes(instrumento.id)
            previstas = [
                c.data_proxima or proxima_calibracao(c.data_calibracao,
                                                     instrumento.periodicidade_meses)
                for c in calibracoes
            ]
            ultima = calibracoes[-1] if calibracoes else None
            data = ultima.data_calibracao if ultima else None
            proxima = previstas[-1] if previstas else None
            anterior = previstas[-2] if len(previstas) > 1 else None
            linhas.append(LinhaCronograma(
                instrumento, data, proxima, situacao(data, proxima, hoje, anterior),
                condicoes[instrumento.id].condicao if instrumento.id in condicoes
                else Condicao.EM_USO,
                ultima.parecer_final if ultima else None,
            ))
        return linhas

    # ---------------------------------------------------------------- lixeira

    def na_lixeira(self, tipo: Tipo, item_id: int) -> bool:
        linha = self._conexao.execute(
            f"SELECT excluido_em FROM {_TABELA[tipo]} WHERE id = ?", (item_id,)
        ).fetchone()
        return linha is not None and linha["excluido_em"] is not None

    @_escrita
    def enviar_para_lixeira(self, tipo: Tipo, item_id: int, motivo: str | None,
                            agora: datetime.datetime) -> None:
        with self._conexao:
            self._conexao.execute(
                f"UPDATE {_TABELA[tipo]} SET excluido_em = ?, motivo_exclusao = ? "
                "WHERE id = ? AND excluido_em IS NULL",
                (agora.isoformat(timespec="seconds"), (motivo or "").strip() or None, item_id),
            )

    def _pai_na_lixeira(self, tipo: Tipo, item_id: int) -> bool:
        coluna = _COLUNA_PAI.get(tipo)
        if coluna is None:
            return False
        pai_id = self._conexao.execute(
            f"SELECT {coluna} FROM {_TABELA[tipo]} WHERE id = ?", (item_id,)
        ).fetchone()[0]
        pai = Tipo.INSTRUMENTO if tipo == Tipo.CALIBRACAO else Tipo.PLANO
        return pai_id is not None and self.na_lixeira(pai, pai_id)

    @_escrita
    def restaurar(self, tipo: Tipo, item_id: int) -> None:
        bloqueio = bloqueio_restaurar(tipo, self._pai_na_lixeira(tipo, item_id))
        if bloqueio:
            raise ErroDeValidacao([bloqueio])
        with self._conexao:
            self._conexao.execute(
                f"UPDATE {_TABELA[tipo]} SET excluido_em = NULL, motivo_exclusao = NULL "
                "WHERE id = ?",
                (item_id,),
            )

    def _tem_dependencias(self, tipo: Tipo, item_id: int) -> bool:
        consultas = {
            Tipo.PLANO: ["SELECT 1 FROM instrumentos WHERE plano_id = ?",
                         "SELECT 1 FROM pontos_plano WHERE plano_id = ?"],
            Tipo.PONTO: ["SELECT 1 FROM pontos_calibracao WHERE ponto_plano_id = ?"],
            Tipo.INSTRUMENTO: ["SELECT 1 FROM calibracoes WHERE instrumento_id = ?"],
            Tipo.CALIBRACAO: [],  # os pontos medidos são apagados junto
        }[tipo]
        return any(self._conexao.execute(sql, (item_id,)).fetchone() for sql in consultas)

    @_escrita
    def excluir_permanentemente(self, tipo: Tipo, item_id: int, confirmacao: str) -> None:
        """Apaga de vez um item que já está na Lixeira (exige digitar EXCLUIR)."""
        if not self.na_lixeira(tipo, item_id):
            raise ErroDeValidacao(["Só é possível excluir permanentemente o que está na Lixeira."])
        bloqueio = bloqueio_exclusao_permanente(
            tipo, confirmacao, self._tem_dependencias(tipo, item_id))
        if bloqueio:
            raise ErroDeValidacao([bloqueio])
        with self._conexao:
            if tipo == Tipo.INSTRUMENTO:  # o histórico de condição vai junto
                self._conexao.execute(
                    "DELETE FROM condicoes WHERE instrumento_id = ?", (item_id,))
            self._conexao.execute(f"DELETE FROM {_TABELA[tipo]} WHERE id = ?", (item_id,))

    def listar_lixeira(self) -> list[ItemLixeira]:
        """Tudo o que está na Lixeira, mais recente primeiro."""
        consulta = """
            SELECT 'Instrumento' AS tipo, id, codigo || ' — ' || tipo AS descricao,
                   excluido_em, motivo_exclusao FROM instrumentos WHERE excluido_em IS NOT NULL
            UNION ALL
            SELECT 'Plano', id, nome, excluido_em, motivo_exclusao
              FROM planos WHERE excluido_em IS NOT NULL
            UNION ALL
            SELECT 'Ponto do plano', p.id, pl.nome || ' — ponto ' || p.ordem || ': ' || p.descricao,
                   p.excluido_em, p.motivo_exclusao
              FROM pontos_plano p JOIN planos pl ON pl.id = p.plano_id
             WHERE p.excluido_em IS NOT NULL
            UNION ALL
            SELECT 'Calibração', c.id,
                   i.codigo || ' — calibração de ' || strftime('%d/%m/%Y', c.data_calibracao),
                   c.excluido_em, c.motivo_exclusao
              FROM calibracoes c JOIN instrumentos i ON i.id = c.instrumento_id
             WHERE c.excluido_em IS NOT NULL
            ORDER BY excluido_em DESC
        """
        return [
            ItemLixeira(Tipo(linha[0]), linha[1], linha[2], linha[3], linha[4])
            for linha in self._conexao.execute(consulta)
        ]
