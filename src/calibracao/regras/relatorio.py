"""Relatórios (pedido de 2026-11-10): o do mês (atual, que muda sozinho, e o final, guardado
quando o mês acaba) e o do ano. Aqui só o que entra em cada um; o PDF é desenhado na interface
(`interface/relatorio_pdf.py`) e o banco junta os dados (`Repositorio.conteudo_do_relatorio`).

Conteúdo (pedido do usuário): números (previstas, feitas, pendentes, vencidas, no prazo, custo
do mês, 12 meses e médio), os gráficos que estão no painel da aba Indicadores, as calibrações do
período e as ALTERAÇÕES. Sem as previstas do mês seguinte.
"""

import calendar
import datetime
from dataclasses import dataclass, field

MENSAL, ANUAL = "Mensal", "Anual"
MESES = ["janeiro", "fevereiro", "março", "abril", "maio", "junho", "julho", "agosto",
         "setembro", "outubro", "novembro", "dezembro"]
# Mais do que isso de instrumentos novos no período (ex.: o cadastro inicial na implantação):
# uma linha com a quantidade, em vez de um por um.
MAXIMO_DE_NOVOS_LISTADOS = 10


@dataclass(frozen=True)
class Periodo:
    tipo: str             # MENSAL ou ANUAL
    ano: int
    mes: int | None = None

    @property
    def inicio(self) -> datetime.date:
        return datetime.date(self.ano, self.mes or 1, 1)

    @property
    def fim(self) -> datetime.date:
        mes = self.mes or 12
        return datetime.date(self.ano, mes, calendar.monthrange(self.ano, mes)[1])

    @property
    def chave(self) -> str:
        """Como fica guardado no banco: "2027-10" (mês) ou "2027" (ano)."""
        return f"{self.ano}-{self.mes:02d}" if self.tipo == MENSAL else str(self.ano)

    @property
    def nome(self) -> str:
        """"outubro de 2027" / "2027"."""
        return f"{MESES[self.mes - 1]} de {self.ano}" if self.tipo == MENSAL else str(self.ano)

    def meses(self) -> list[datetime.date]:
        """Primeiro dia de cada mês do período."""
        if self.tipo == MENSAL:
            return [self.inicio]
        return [datetime.date(self.ano, m, 1) for m in range(1, 13)]

    @classmethod
    def da_chave(cls, chave: str) -> "Periodo":
        if "-" in chave:
            ano, mes = chave.split("-")
            return cls(MENSAL, int(ano), int(mes))
        return cls(ANUAL, int(chave))

    def acabou(self, hoje: datetime.date) -> bool:
        return hoje > self.fim

    def nome_do_arquivo(self) -> str:
        if self.tipo == MENSAL:
            return f"DQ-05 Relatório {self.chave} ({MESES[self.mes - 1]} de {self.ano}).pdf"
        return f"DQ-05 Relatório anual {self.ano}.pdf"


def mes_atual(hoje: datetime.date) -> Periodo:
    return Periodo(MENSAL, hoje.year, hoje.month)


def ano_atual(hoje: datetime.date) -> Periodo:
    return Periodo(ANUAL, hoje.year)


def pendentes(implantacao: datetime.date | None, hoje: datetime.date,
              ja_guardados: set[str]) -> list[Periodo]:
    """Relatórios finais que já deviam existir e ainda não foram guardados: cada mês que acabou
    desde a implantação e cada ano que acabou (o 1º ano só com os meses de uso). Em ordem."""
    if implantacao is None:
        return []
    faltam = []
    atual = datetime.date(implantacao.year, implantacao.month, 1)
    while True:
        periodo = Periodo(MENSAL, atual.year, atual.month)
        if not periodo.acabou(hoje):
            break
        if periodo.chave not in ja_guardados:
            faltam.append(periodo)
        if atual.month == 12:
            anual = Periodo(ANUAL, atual.year)
            if anual.chave not in ja_guardados:
                faltam.append(anual)
        atual = datetime.date(atual.year + (atual.month == 12), atual.month % 12 + 1, 1)
    return faltam


@dataclass
class Numero:
    rotulo: str
    valor: str
    cor: str = ""   # "" normal; "certo", "aviso", "erro"


@dataclass
class LinhaDoRelatorio:
    codigo: str
    tipo: str
    localizacao: str
    feita_em: str          # dd/mm/aaaa ou "—"
    certificado: str
    laboratorio: str
    situacao: str          # parecer final (feita) ou "Pendente" / "Vencida"
    custo: str


@dataclass
class ConteudoRelatorio:
    periodo: Periodo
    final: bool                   # True = relatório final (o período acabou)
    referencia: datetime.date     # "hoje" do relatório: fim do período ou o dia de hoje
    gerado_em: datetime.datetime
    numeros: list[Numero] = field(default_factory=list)
    linhas: list[LinhaDoRelatorio] = field(default_factory=list)
    alteracoes: list[tuple[str, str]] = field(default_factory=list)  # (erro/aviso/info, texto)

    @property
    def titulo(self) -> str:
        if self.periodo.tipo == MENSAL:
            return f"RELATÓRIO DE {self.periodo.nome.upper()}"
        return f"RELATÓRIO DO ANO DE {self.periodo.ano}"

    @property
    def subtitulo(self) -> str:
        quando = f"{self.gerado_em:%d/%m/%Y %H:%M}"
        if self.final:
            tipo = "Relatório final do mês" if self.periodo.tipo == MENSAL else \
                "Relatório final do ano"
            return f"{tipo} · dados até {self.periodo.fim:%d/%m/%Y} · gerado em {quando}"
        return (f"Em andamento (muda a cada calibração ou alteração) · dados até "
                f"{self.referencia:%d/%m/%Y} · gerado em {quando}")


def dinheiro(valor: float | None) -> str:
    if valor is None:
        return "—"
    return "R$ " + f"{valor:,.2f}".replace(",", "X").replace(".", ",").replace("X", ".")
