"""
Incertezas históricas extraídas da planilha original do CALIB.

IMPORTANTE:
- Os valores são registros históricos, não critérios oficiais aprovados.
- As unidades precisam ser confirmadas antes do uso metrológico definitivo.
- Valores negativos e zeros são preservados exatamente como informados.
- A associação é feita pelo código do equipamento e pelo ponto.
"""

from collections import defaultdict


AVISO_HISTORICO = (
    "Valor histórico da planilha original. "
    "Confirmar unidade e validade metrológica antes do uso oficial."
)

AVISO_DURometro = (
    "Valor histórico do durômetro: confirmar os registros negativos "
    "no documento original."
)


def _codigos(texto):
    """Converte uma lista de códigos separados por espaço em conjunto."""
    return set(texto.split())


# Cada especificação contém os pontos na ordem informada na planilha.
# O pareamento por ordem somente será usado quando a sequência puder
# ser associada com segurança ao plano de calibração.

PAQUIMETROS = {}

for codigo in _codigos(
    "PAQ-002 PAQ-010 PAQ-015"
):
    PAQUIMETROS[codigo] = {
        "pontos": [
            0, 1.1, 60, 120, 180, 240, 300, 50, 50, 50
        ],
        "incertezas": [0.01] * 10,
    }

PAQUIMETROS["PAQ-011"] = {
    "pontos": [
        0, 1.1, 60, 120, 180, 240, 300, 50, 50, 50
    ],
    "incertezas": [
        0.01, 0.01, 0.01, 0.01, 0.01,
        0.01, 0.01, 0.01, 0.01, 0.1,
    ],
}

for codigo in _codigos(
    "PAQ-004 PAQ-005 PAQ-006 PAQ-014 PAQ-016 PAQ-017"
):
    PAQUIMETROS[codigo] = {
        "pontos": [
            0, 1.1, 100, 200, 300, 400, 500, 90, 20
        ],
        "incertezas": [0.01] * 9,
    }

for codigo in _codigos("PAQ-003 PAQ-009"):
    PAQUIMETROS[codigo] = {
        "pontos": [
            0, 1.1, 160, 320, 480, 640, 800, 90, 20
        ],
        "incertezas": [0.01] * 9,
    }

PAQUIMETROS["PAQ-012"] = {
    "pontos": [
        0, 1.1, 30, 60, 90, 120, 150, 50, 50, 50
    ],
    "incertezas": [0.01] * 10,
}


# Micrômetros: 11 pontos dimensionais.
PONTOS_MICROMETRO = [
    0, 2.5, 5.1, 7.7, 10.3, 12.9,
    15, 17.6, 20.2, 22.8, 25,
]

MICROMETROS = {
    "MIC-001": {
        "pontos": PONTOS_MICROMETRO,
        "incertezas": [0.003] * 11,
    },
    "MIC-003": {
        "pontos": PONTOS_MICROMETRO,
        "incertezas": [0.002] * 11,
    },
    "MIC-004": {
        "pontos": PONTOS_MICROMETRO,
        "incertezas": [
            0.001, 0.001, 0.001, 0.002, 0.002,
            0.001, 0.002, 0.002, 0.002, 0.002, 0.002,
        ],
    },
    "MIC-005": {
        "pontos": PONTOS_MICROMETRO,
        "incertezas": [0.001] * 11,
    },
}

for codigo in _codigos(
    "MIC-006 MIC-007 MIC-008 MIC-009 "
    "MIC-010 MIC-011 MIC-013 MIC-014"
):
    MICROMETROS[codigo] = {
        "pontos": PONTOS_MICROMETRO,
        "incertezas": [0.001] * 11,
    }

MICROMETROS["MIC-012"] = {
    "pontos": PONTOS_MICROMETRO + ["PLANEZA", "PARALELISMO"],
    "incertezas": [0.001] * 11 + [0, 0],
}


# Trenas: os pontos nominais registrados são os mesmos.
PONTOS_TRENA = [300, 900, 1500, 2100, 2700]

TRENAS = {}

for codigo in _codigos(
    "TRE-037 TRE-111 TRE-129 TRE-130 TRE-152 TRE-169 "
    "TRE-170 TRE-171 TRE-172 TRE-191 TRE-192 TRE-196 "
    "TRE-197 TRE-198 TRE-199"
):
    TRENAS[codigo] = {
        "pontos": PONTOS_TRENA,
        "incertezas": [0.2] * 5,
        "capacidade_registrada": "3000 / 3000 mm",
    }

for codigo in _codigos(
    "TRE-116 TRE-120 TRE-148 TRE-149 TRE-150 TRE-193 "
    "TRE-195 TRE-140 TRE-160 TRE-161 TRE-162 TRE-163 "
    "TRE-164 TRE-165"
):
    TRENAS[codigo] = {
        "pontos": PONTOS_TRENA,
        "incertezas": [0.2] * 5,
        "capacidade_registrada": "3500 / 3000 mm",
    }

for codigo in (
    _codigos(
        "TRE-136 TRE-138 TRE-144 TRE-151 TRE-153 "
        "TRE-166 TRE-167 TRE-168 TRE-194"
    )
    | {f"TRE-{numero}" for numero in range(174, 191)}
    | {f"TRE-{numero}" for numero in range(201, 234)}
):
    TRENAS[codigo] = {
        "pontos": PONTOS_TRENA,
        "incertezas": [0.2] * 5,
        "capacidade_registrada": "5000 / 3000 mm",
    }

for codigo in _codigos(
    "TRE-052 TRE-132 TRE-137 TRE-141 TRE-143"
):
    TRENAS[codigo] = {
        "pontos": PONTOS_TRENA,
        "incertezas": [0.2] * 5,
        "capacidade_registrada": None,
        "revisar_capacidade": True,
    }


# Réguas graduadas.
REGUAS = {
    "ESC-001": {
        "pontos": [0, 100, 200, 300, 400, 500, 600,
                   700, 800, 900, 1000],
        "incertezas": [0.2] * 11,
    },
    "ESC-004": {
        "pontos": [4, 5.5, 7, 8.5, 10,
                   "ISENTO DE DEFORMACOES", "GRADUACAO LEGIVEL"],
        "incertezas": [0.007, 0.005, 0.005, 0.005, 0.008,
                       0.007, 0.005],
    },
    "ESC-005": {
        "pontos": list(range(2, 16)),
        "incertezas": [
            0.004, 0.006, 0.004, 0.005, 0.004, 0.004,
            0.004, 0.003, 0.004, 0.006, 0.004, 0.005,
            0.004, 0.003,
        ],
    },
}

PONTOS_REGUAS_008_009_010 = [
    1, 2, 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 14, 15
]
INCERTEZAS_REGUAS_008_009_010 = [
    0.004, 0.004, 0.003, 0.003, 0.003, 0.003, 0.003,
    0.004, 0.004, 0.003, 0.004, 0.003, 0.003, 0.003,
]

for codigo in _codigos("ESC-008 ESC-009 ESC-010"):
    REGUAS[codigo] = {
        "pontos": PONTOS_REGUAS_008_009_010,
        "incertezas": INCERTEZAS_REGUAS_008_009_010,
    }


# Goniômetros.
GONIOMETROS = {
    "GON-001": {
        "pontos": [0, 30, 31, 60, 90],
        "incertezas": [0.07] * 5,
    },
    "GON-002": {
        "pontos": [0, 15, 30, 45, 60, 90],
        "incertezas": [0.08] * 6,
    },
    "GON-004": {
        "pontos": [0, 15, 30, 45, 60, 90],
        "incertezas": [0.07] * 6,
        "observacao": "Registros em diferentes quadrantes.",
    },
}


# Durômetro: os valores negativos foram preservados.
DUROMETRO_DUR001 = {
    "HR15T": {
        "67-80": 0.94,
        "81-87": 0.51,
        "88-93": -0.57,
    },
    "HRB": {
        "10-50": 0.73,
        "60-80": 0.71,
        "85-100": -0.60,
    },
    "HRC": {
        "10-30": 0.84,
        "35-55": 0.63,
        "60-70": -0.88,
    },
}


# Lâminas de folga.
PONTOS_LAMINAS = [
    0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09,
    0.10, 0.15, 0.20, 0.25, 0.30, 0.40, 0.50, 0.75, 1.00,
]

LAMINAS_FOLGA = {
    codigo: {
        "pontos": PONTOS_LAMINAS,
        "incertezas": [0.001] * len(PONTOS_LAMINAS),
    }
    for codigo in _codigos(
        "LAF-010 LAF-011 LAF-012 LAF-013 LAF-014"
    )
}


# Manômetros: associação direta ponto -> incerteza.
MANOMETROS = {
    "MN-001": {
        0: 0.21, 5: 0.37, 10: 0.42, 15: 0.33, 20: 0.21,
    },
    "MN-004": {
        0: 0.09, 2: 0.09, 6: 0.10, 10: 0.10, 14: 0.09,
    },
    "MN-005": {
        0: 0.05, 4: 0.05, 7: 0.06, 10: 0.07, 14: 0.05,
    },
    "MN-006": {
        0: 0.21, 5: 0.28, 10: 0.21, 15: 0.25, 20: 0.21,
    },
    "MAN-004": {
        0: 0.09, 2: 0.09, 6: 0.09, 10: 0.09, 14: 0.09,
    },
    "MAN-005": {
        0: 0, 4: 0.09, 7: 0.09, 10: 0.09, 14: 0.09,
    },
    "MAN-006": {
        0: 0.09, 4: 0.09, 7: 0.09, 10: 0.09, 14: 0.09,
    },
}


# Válvulas de segurança.
VALVULAS_SEGURANCA = {
    "VS-001": {"ponto": 8, "incerteza": 0.15},
    "VS-002": {"ponto": 8, "incerteza": 0.15},
}


# Balanças: a incerteza é constante para os pontos numéricos
# informados. Os pontos por diferença e repetições não são
# reconstruídos automaticamente sem a ordem original.
BALANCAS = {
    "BAL-002": {"incerteza": 1, "resolucao": 1},
    "BAL-004": {"incerteza": 1, "resolucao": 1},
    "BAL-003": {"incerteza": 5, "resolucao": 5},
    "BAL-005": {"incerteza": 5, "resolucao": 5},
}


def _numero(valor):
    """Converte números e textos numéricos para comparação segura."""
    if valor is None or isinstance(valor, bool):
        return None

    try:
        return float(str(valor).replace(",", ".").strip())
    except (TypeError, ValueError):
        return None


def _texto_normalizado(valor):
    return (
        str(valor or "")
        .strip()
        .upper()
        .replace("Á", "A")
        .replace("À", "A")
        .replace("Ã", "A")
        .replace("É", "E")
        .replace("Ê", "E")
        .replace("Í", "I")
        .replace("Ó", "O")
        .replace("Ô", "O")
        .replace("Õ", "O")
        .replace("Ú", "U")
        .replace("Ç", "C")
    )


def _obter_valor_por_ponto(codigo, nominal, tabela):
    if codigo not in tabela or nominal is None:
        return None

    mapa = tabela[codigo]
    numero = _numero(nominal)

    if numero is None:
        return None

    for ponto, incerteza in mapa.items():
        if abs(float(ponto) - numero) < 1e-9:
            return incerteza

    return None


def obter_incerteza_referencia(codigo, ponto, indice=0):
    """
    Retorna (valor, observacao) para um ponto de calibração.

    `indice` é a posição do ponto na lista ordenada, começando em zero.
    Para pontos que não possam ser associados com segurança, retorna
    (None, aviso), sem inventar um valor.
    """
    codigo = _texto_normalizado(codigo)
    nominal = ponto["valor_nominal"]
    descricao = _texto_normalizado(ponto["descricao"])

    # Manômetros: valores individualizados por ponto.
    if codigo in MANOMETROS:
        valor = _obter_valor_por_ponto(
            codigo, nominal, MANOMETROS
        )
        if valor is not None:
            observacao = AVISO_HISTORICO
            if codigo == "MAN-005" and _numero(nominal) == 0:
                observacao += " O zero está registrado; confirmar."
            return valor, observacao
        return None, AVISO_HISTORICO

    # Balanças: valor constante para ponto numérico registrado.
    if codigo in BALANCAS:
        if _numero(nominal) is not None:
            return BALANCAS[codigo]["incerteza"], AVISO_HISTORICO
        return None, AVISO_HISTORICO

    # Válvulas: somente associar ao ponto 8 informado.
    if codigo in VALVULAS_SEGURANCA:
        spec = VALVULAS_SEGURANCA[codigo]
        if _numero(nominal) == spec["ponto"]:
            return spec["incerteza"], AVISO_HISTORICO
        return None, AVISO_HISTORICO

    # Durômetro: localizar escala e faixa na descrição do ponto.
    if codigo == "DUR-001":
        for escala, faixas in DUROMETRO_DUR001.items():
            if escala in descricao:
                for faixa, valor in faixas.items():
                    faixa_sem_hifen = faixa.replace("-", "–")
                    if faixa in descricao or faixa_sem_hifen in descricao:
                        return valor, AVISO_DURometro
        return None, AVISO_DURometro

    # Demais instrumentos usam sequências explícitas.
    tabelas = (
        PAQUIMETROS,
        MICROMETROS,
        TRENAS,
        REGUAS,
        GONIOMETROS,
        LAMINAS_FOLGA,
    )

    for tabela in tabelas:
        if codigo not in tabela:
            continue

        spec = tabela[codigo]
        pontos = spec["pontos"]
        incertezas = spec["incertezas"]

        if indice < 0 or indice >= len(incertezas):
            return None, AVISO_HISTORICO

        ponto_esperado = pontos[indice]
        incerteza = incertezas[indice]

        if isinstance(ponto_esperado, str):
            # Pontos qualitativos como planeza, paralelismo e legibilidade.
            if ponto_esperado in descricao:
                return incerteza, AVISO_HISTORICO
            return None, AVISO_HISTORICO

        nominal_numero = _numero(nominal)
        esperado_numero = _numero(ponto_esperado)

        if (
            nominal_numero is not None
            and esperado_numero is not None
            and abs(nominal_numero - esperado_numero) < 1e-9
        ):
            return incerteza, AVISO_HISTORICO

        # Se a descrição contém o ponto esperado, aceitar a associação.
        if (
            nominal_numero is None
            and str(ponto_esperado) in descricao
        ):
            return incerteza, AVISO_HISTORICO

        return None, AVISO_HISTORICO

    return None, (
        "Nenhuma incerteza histórica localizada para este código "
        "e ponto. Não preencher automaticamente."
    )