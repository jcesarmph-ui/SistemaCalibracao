"""Indicadores: gráficos que o próprio usuário monta (pedido de 2026-11-10, como um Power BI
sem IA) e os números fixos do painel. Sem tela: a aba Indicadores e o relatório do mês usam isto.

Um gráfico é uma `DefinicaoGrafico` (o que ver · separado por · só os que… · cores · período ·
jeito · título), guardada no banco como JSON. `calcular` transforma a definição + as calibrações
em categorias e séries prontas para desenhar.
"""

import datetime
import json
from collections import defaultdict
from dataclasses import asdict, dataclass, field

from calibracao.regras.avaliacao import Resultado, desvio_final

# --------------------------------------------------------------------------- o que dá para escolher
QTD_CALIBRACOES = "Quantidade de calibrações"
CUSTO = "Custo das calibrações (R$)"
CUSTO_MEDIO = "Custo médio por calibração (R$)"
NO_PRAZO = "% de calibrações feitas no prazo"
PERTO_DO_LIMITE = "Mais perto do limite (% da tolerância usada)"
QTD_INSTRUMENTOS = "Quantidade de instrumentos"
MEDIDAS = [QTD_CALIBRACOES, CUSTO, CUSTO_MEDIO, NO_PRAZO, PERTO_DO_LIMITE, QTD_INSTRUMENTOS]

MES, ANO, TIPO, LABORATORIO, LOCALIZACAO, PARECER, PRAZO, INSTRUMENTO = (
    "Mês", "Ano", "Tipo de instrumento", "Laboratório", "Localização", "Parecer final",
    "Prazo (no prazo / com atraso)", "Instrumento")
SEPARAR = [MES, ANO, TIPO, LABORATORIO, LOCALIZACAO, PARECER, PRAZO, INSTRUMENTO]
SEM_CORES = "Não (uma cor só)"
CORES_POR = [SEM_CORES, PARECER, PRAZO, LABORATORIO]
ULTIMOS_12, ESTE_ANO, ANO_PASSADO, TUDO = "Últimos 12 meses", "Este ano", "Ano passado", "Tudo"
PERIODOS = [ULTIMOS_12, ESTE_ANO, ANO_PASSADO, TUDO]
BARRAS, DEITADAS, LINHA = "Barras em pé", "Barras deitadas", "Linha"
FORMAS = [BARRAS, DEITADAS, LINHA]
FILTRAVEIS = [PARECER, PRAZO, TIPO, LABORATORIO, LOCALIZACAO]
TODOS = "Todos"
NO_PRAZO_TXT, COM_ATRASO_TXT = "No prazo", "Com atraso"
SEM_LABORATORIO = "Sem laboratório"
MAXIMO_DE_ITENS = 12   # mais do que isso, mostra os maiores e avisa
PIORES_NO_LIMITE = 10
MESES_CURTOS = ["jan", "fev", "mar", "abr", "mai", "jun", "jul", "ago", "set", "out", "nov",
                "dez"]


@dataclass
class DefinicaoGrafico:
    medida: str = QTD_CALIBRACOES
    separar: str = MES
    cor: str = SEM_CORES
    filtros: dict[str, str] = field(default_factory=dict)
    periodo: str = ULTIMOS_12
    forma: str = BARRAS
    titulo: str = ""

    def para_json(self) -> str:
        return json.dumps(asdict(self), ensure_ascii=False)

    @classmethod
    def de_json(cls, texto: str) -> "DefinicaoGrafico":
        dados = json.loads(texto)
        return cls(**{k: v for k, v in dados.items() if k in cls.__dataclass_fields__})


# Os 4 gráficos com que o painel começa (escolhidos pelo usuário em 2026-11-10); os números de
# custo (mês, 12 meses, médio) ficam fixos em cima do painel.
PAINEL_INICIAL = [
    DefinicaoGrafico(QTD_CALIBRACOES, MES, PRAZO,
                     titulo="CALIBRAÇÕES POR MÊS (NO PRAZO × COM ATRASO)"),
    DefinicaoGrafico(CUSTO, MES, titulo="CUSTO DE CALIBRAÇÃO POR MÊS"),
    DefinicaoGrafico(CUSTO, LABORATORIO, forma=DEITADAS,
                     titulo="CUSTO POR LABORATÓRIO (12 MESES)"),
    DefinicaoGrafico(PERTO_DO_LIMITE, titulo="MAIS PERTO DO LIMITE"),
]


@dataclass
class CalibracaoParaIndicador:
    """Uma calibração (fora da Lixeira), já com o que os gráficos precisam."""
    data: datetime.date
    instrumento: str
    tipo: str
    locais: list[str]
    laboratorio: str
    parecer: str
    prazo: str          # "No prazo" / "Com atraso" (feita depois do mês previsto)
    custo: float        # sem custo registrado = 0
    limite: float | None  # % da tolerância usada pelo pior ponto (None = sem ponto numérico)


@dataclass
class InstrumentoParaIndicador:
    codigo: str
    tipo: str
    locais: list[str]


@dataclass
class ResultadoGrafico:
    categorias: list[str]
    series: dict[str, list[float]]   # nome da série ("" = uma só) → um valor por categoria
    unidade: str = ""                # "R$", "%" ou "" (quantidade)
    aviso: str = ""                  # por que não há gráfico (vazio = há gráfico)
    nota: str = ""                   # ex.: "Mostrando os 12 maiores de 30"

    @property
    def vazio(self) -> bool:
        return not self.categorias


# --------------------------------------------------------------------------- o que faz sentido
def separacoes_validas(medida: str) -> list[str]:
    """Instrumentos não têm data, laboratório nem parecer: só por tipo ou localização."""
    if medida == QTD_INSTRUMENTOS:
        return [TIPO, LOCALIZACAO]
    if medida == PERTO_DO_LIMITE:
        return [INSTRUMENTO]
    return list(SEPARAR)


def pode_dividir_em_cores(medida: str) -> bool:
    """Média e % não se somam: não dá para empilhar cores."""
    return medida in (QTD_CALIBRACOES, CUSTO)


def usa_periodo(medida: str) -> bool:
    return medida not in (QTD_INSTRUMENTOS, PERTO_DO_LIMITE)


def filtros_validos(medida: str) -> list[str]:
    if medida == PERTO_DO_LIMITE:
        return []
    if medida == QTD_INSTRUMENTOS:
        return [TIPO, LOCALIZACAO]
    return list(FILTRAVEIS)


def ajustar(definicao: DefinicaoGrafico) -> DefinicaoGrafico:
    """Tira o que não faz sentido para a medida escolhida (o montador só oferece o que vale)."""
    validas = separacoes_validas(definicao.medida)
    separar = definicao.separar if definicao.separar in validas else validas[0]
    cor = definicao.cor if pode_dividir_em_cores(definicao.medida) else SEM_CORES
    filtros = {k: v for k, v in definicao.filtros.items()
               if k in filtros_validos(definicao.medida) and v and v != TODOS}
    forma = DEITADAS if definicao.medida == PERTO_DO_LIMITE else definicao.forma
    return DefinicaoGrafico(definicao.medida, separar, cor, filtros, definicao.periodo, forma,
                            definicao.titulo)


def titulo_automatico(definicao: DefinicaoGrafico) -> str:
    """Ex.: "CALIBRAÇÕES REPROVADAS POR MÊS"."""
    if definicao.medida == PERTO_DO_LIMITE:
        return "MAIS PERTO DO LIMITE"
    medida = {QTD_CALIBRACOES: "CALIBRAÇÕES", CUSTO: "CUSTO DAS CALIBRAÇÕES",
              CUSTO_MEDIO: "CUSTO MÉDIO POR CALIBRAÇÃO", NO_PRAZO: "% NO PRAZO",
              QTD_INSTRUMENTOS: "INSTRUMENTOS"}[definicao.medida]
    jeito = {"Aprovado": "APROVADAS", "Orientação indicativa": "COM ORIENTAÇÃO INDICATIVA",
             "Reprovado - Desativado": "REPROVADAS", NO_PRAZO_TXT: "NO PRAZO",
             COM_ATRASO_TXT: "COM ATRASO"}
    filtros = [jeito.get(v, f"· {v.upper()}") for v in definicao.filtros.values()]
    if filtros:
        medida += " " + " ".join(filtros)
    texto = f"{medida} POR {definicao.separar.split(' (')[0].upper()}"
    if usa_periodo(definicao.medida) and definicao.periodo != ULTIMOS_12:
        texto += f" ({definicao.periodo.upper()})"
    return texto


def opcoes_de_filtro(calibracoes: list[CalibracaoParaIndicador],
                     instrumentos: list[InstrumentoParaIndicador]) -> dict[str, list[str]]:
    """As escolhas de cada "Só os que…", com o que existe no banco."""
    from calibracao.regras.condicao import ParecerFinal

    tipos = {c.tipo for c in calibracoes} | {i.tipo for i in instrumentos}
    locais = {local for c in calibracoes for local in c.locais}
    locais |= {local for i in instrumentos for local in i.locais}
    return {PARECER: [p.value for p in ParecerFinal],
            PRAZO: [NO_PRAZO_TXT, COM_ATRASO_TXT],
            TIPO: sorted(tipos),
            LABORATORIO: sorted({c.laboratorio for c in calibracoes}),
            LOCALIZACAO: sorted(locais)}


# --------------------------------------------------------------------------- períodos e meses
def _mes_somado(ano: int, mes: int, meses: int) -> tuple[int, int]:
    total = ano * 12 + (mes - 1) + meses
    return total // 12, total % 12 + 1


def meses_do_periodo(periodo: str, referencia: datetime.date,
                     primeira: datetime.date | None = None) -> list[tuple[int, int]]:
    """(ano, mês) de cada mês do período, terminando no mês de `referencia`."""
    fim = (referencia.year, referencia.month)
    if periodo == ULTIMOS_12:
        inicio = _mes_somado(*fim, -11)
    elif periodo == ESTE_ANO:
        inicio = (referencia.year, 1)
    elif periodo == ANO_PASSADO:
        inicio, fim = (referencia.year - 1, 1), (referencia.year - 1, 12)
    else:
        inicio = (primeira.year, primeira.month) if primeira else fim
    meses, atual = [], inicio
    while atual <= fim:
        meses.append(atual)
        atual = _mes_somado(*atual, 1)
    return meses


def rotulo_do_mes(ano: int, mes: int) -> str:
    return f"{MESES_CURTOS[mes - 1]}/{str(ano)[2:]}"


def no_periodo(data: datetime.date, periodo: str, referencia: datetime.date) -> bool:
    if periodo == TUDO:
        return data <= referencia
    meses = meses_do_periodo(periodo, referencia)
    return meses[0] <= (data.year, data.month) <= meses[-1] and data <= referencia


# --------------------------------------------------------------------------- mais perto do limite
def limite_usado(pontos) -> float | None:
    """% da tolerância que o pior ponto numérico usou, já com a U (100% = no limite; mais de
    100% = fora). Ponto com nominal: desvio final ÷ tolerância do lado para onde foi. Pontos de
    limite (mín./máx.), qualitativos, não aplicáveis ou sem U ficam de fora.

    `pontos` são os `PontoRegistrado` da calibração (a "foto" do plano + o medido)."""
    piores = []
    for ponto in pontos:
        if (ponto.tipo != "NUMERICO" or ponto.valor is None
                or ponto.resultado == Resultado.NAO_APLICAVEL):
            continue
        desvio = ponto.valor - ponto.valor_nominal if ponto.valor_nominal is not None \
            else ponto.valor
        final = desvio_final(desvio, ponto.incerteza, ponto.tolerancia_inferior,
                             ponto.tolerancia_superior, bool(ponto.incerteza_nao_aplica))
        if final is None:
            continue
        lados = []
        superior, inferior = ponto.tolerancia_superior, ponto.tolerancia_inferior
        if final.dos_dois_lados:  # desvio zero: ± U contra o lado mais apertado
            if superior and superior > 0:
                lados.append(final.valor / superior)
            if inferior and inferior < 0:
                lados.append(final.valor / -inferior)
        elif final.valor >= 0 and superior and superior > 0:
            lados.append(final.valor / superior)
        elif final.valor < 0 and inferior and inferior < 0:
            lados.append(final.valor / inferior)
        if lados:
            piores.append(100 * max(lados))
    return round(max(piores), 1) if piores else None


# --------------------------------------------------------------------------- cálculo
def _chave(calibracao: CalibracaoParaIndicador, separar: str) -> list[str]:
    """Em que categoria(s) a calibração entra (um instrumento em dois locais conta nos dois,
    como no filtro da lista)."""
    if separar == MES:
        return [f"{calibracao.data.year}-{calibracao.data.month:02d}"]
    if separar == LOCALIZACAO:
        return calibracao.locais or ["Sem localização"]
    return [{ANO: str(calibracao.data.year), TIPO: calibracao.tipo,
             LABORATORIO: calibracao.laboratorio, PARECER: calibracao.parecer,
             PRAZO: calibracao.prazo, INSTRUMENTO: calibracao.instrumento}[separar]]


def _passa(calibracao: CalibracaoParaIndicador, filtros: dict[str, str]) -> bool:
    for campo, valor in filtros.items():
        if campo == LOCALIZACAO:
            if valor not in calibracao.locais:
                return False
        elif _chave(calibracao, campo)[0] != valor:
            return False
    return True


def _cortar(categorias, series, total):
    """Mais de 12 itens: os 12 maiores, com aviso."""
    nota = ""
    if len(categorias) > MAXIMO_DE_ITENS:
        nota = (f"Mostrando os {MAXIMO_DE_ITENS} maiores de {len(categorias)} (os outros "
                "ficaram de fora).")
    ordem = sorted(range(len(categorias)), key=lambda i: (-total[i], categorias[i]))
    ordem = ordem[:MAXIMO_DE_ITENS]
    return ([categorias[i] for i in ordem], {s: [v[i] for i in ordem] for s, v in series.items()},
            nota)


def calcular(definicao: DefinicaoGrafico, calibracoes: list[CalibracaoParaIndicador],
             instrumentos: list[InstrumentoParaIndicador], referencia: datetime.date,
             intervalo: tuple[datetime.date, datetime.date] | None = None) -> ResultadoGrafico:
    """Categorias e séries do gráfico. `referencia` = o dia que conta como "hoje" (no relatório,
    o último dia do período). `intervalo`: no relatório, "Mais perto do limite" usa só as
    calibrações do período (mês ou ano); no painel, a última de cada instrumento."""
    definicao = ajustar(definicao)
    medida = definicao.medida
    if medida == PERTO_DO_LIMITE:
        return _perto_do_limite(calibracoes, referencia, intervalo)
    if medida == QTD_INSTRUMENTOS:
        return _instrumentos(definicao, instrumentos)
    linhas = [c for c in calibracoes if no_periodo(c.data, definicao.periodo, referencia)
              and _passa(c, definicao.filtros)]
    if not linhas:
        return ResultadoGrafico([], {}, aviso="Nenhuma calibração com essas escolhas: o "
                                              "gráfico ficaria vazio.")
    cor = definicao.cor
    grupos: dict[str, dict[str, list]] = defaultdict(lambda: defaultdict(list))
    for linha in linhas:
        serie = "" if cor == SEM_CORES else _chave(linha, cor)[0]
        for categoria in _chave(linha, definicao.separar):
            grupos[serie][categoria].append(linha)

    def valor(lista: list[CalibracaoParaIndicador]) -> float:
        if medida == QTD_CALIBRACOES:
            return len(lista)
        if medida == CUSTO:
            return sum(c.custo for c in lista)
        if not lista:
            return 0
        if medida == CUSTO_MEDIO:
            return sum(c.custo for c in lista) / len(lista)
        return 100 * sum(c.prazo == NO_PRAZO_TXT for c in lista) / len(lista)

    ordem_series = sorted(grupos, key=lambda s: (ORDEM_DAS_SERIES.get(s, 99), s))
    if definicao.separar == MES:
        primeira = min(c.data for c in linhas)
        chaves = [f"{a}-{m:02d}" for a, m in meses_do_periodo(definicao.periodo, referencia,
                                                              primeira)]
        series = {s: [valor(grupos[s].get(c, [])) for c in chaves] for s in ordem_series}
        categorias = [rotulo_do_mes(int(c[:4]), int(c[5:])) for c in chaves]
        nota = ""
    else:
        chaves = sorted({c for g in grupos.values() for c in g})
        series = {s: [valor(grupos[s].get(c, [])) for c in chaves] for s in ordem_series}
        total = [sum(v[i] for v in series.values()) for i in range(len(chaves))]
        categorias, series, nota = _cortar(chaves, series, total)
    unidade = ("R$" if medida in (CUSTO, CUSTO_MEDIO) else "%" if medida == NO_PRAZO else "")
    return ResultadoGrafico(categorias, series, unidade, nota=nota)


# Ordem fixa das cores conhecidas (verde, amarelo, vermelho), para não trocarem de lugar.
ORDEM_DAS_SERIES = {"Aprovado": 0, "Orientação indicativa": 1, "Reprovado - Desativado": 2,
                    NO_PRAZO_TXT: 0, COM_ATRASO_TXT: 1}


def _perto_do_limite(calibracoes, referencia, intervalo) -> ResultadoGrafico:
    if intervalo:
        escolhidas = [c for c in calibracoes if intervalo[0] <= c.data <= intervalo[1]]
    else:
        ultima = {}
        for c in sorted(calibracoes, key=lambda c: c.data):
            if c.data <= referencia:
                ultima[c.instrumento] = c
        escolhidas = list(ultima.values())
    escolhidas = [c for c in escolhidas if c.limite is not None]
    if not escolhidas:
        return ResultadoGrafico([], {}, aviso="Nenhuma calibração com ponto numérico avaliado "
                                              "(com tolerância) ainda.")
    piores = sorted(escolhidas, key=lambda c: (-c.limite, c.instrumento))[:PIORES_NO_LIMITE]
    return ResultadoGrafico([c.instrumento for c in piores], {"": [c.limite for c in piores]},
                            "%")


def _instrumentos(definicao, instrumentos) -> ResultadoGrafico:
    contagem: dict[str, int] = defaultdict(int)
    for inst in instrumentos:
        if TIPO in definicao.filtros and inst.tipo != definicao.filtros[TIPO]:
            continue
        if LOCALIZACAO in definicao.filtros and definicao.filtros[LOCALIZACAO] not in inst.locais:
            continue
        chaves = [inst.tipo] if definicao.separar == TIPO else (inst.locais or
                                                                ["Sem localização"])
        for chave in chaves:
            contagem[chave] += 1
    if not contagem:
        return ResultadoGrafico([], {}, aviso="Nenhum instrumento com essas escolhas.")
    chaves = sorted(contagem)
    categorias, series, nota = _cortar(chaves, {"": [contagem[c] for c in chaves]},
                                       [contagem[c] for c in chaves])
    return ResultadoGrafico(categorias, series, nota=nota)


# --------------------------------------------------------------------------- números fixos
@dataclass
class NumerosDoPainel:
    custo_do_mes: float
    custo_12_meses: float
    custo_medio_mes: float      # média por mês nos 12 meses (ou nos meses de uso, se menos)
    no_prazo: float | None      # % das feitas nos 12 meses (None = nenhuma feita)
    feitas_12_meses: int


def numeros(calibracoes: list[CalibracaoParaIndicador], referencia: datetime.date,
            implantacao: datetime.date | None = None) -> NumerosDoPainel:
    """No 1º ano a média divide pelos meses de uso (desde a implantação), não por 12."""
    do_mes = [c for c in calibracoes
              if (c.data.year, c.data.month) == (referencia.year, referencia.month)
              and c.data <= referencia]
    doze = [c for c in calibracoes if no_periodo(c.data, ULTIMOS_12, referencia)]
    custo_12 = sum(c.custo for c in doze)
    no_prazo = (100 * sum(c.prazo == NO_PRAZO_TXT for c in doze) / len(doze)) if doze else None
    meses = 12
    if implantacao is not None:
        uso = (referencia.year - implantacao.year) * 12 + referencia.month - implantacao.month + 1
        meses = max(1, min(12, uso))
    return NumerosDoPainel(sum(c.custo for c in do_mes), custo_12, custo_12 / meses, no_prazo,
                           len(doze))
