import sys
from pathlib import Path
from datetime import datetime

# Permite importar o módulo do banco
BASE_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(BASE_DIR))

from app.database.db import conectar, criar_banco


# ============================================================
# DADOS DOS PLANOS
# ============================================================

PLANOS = []


def adicionar_plano(
    tipo,
    nome,
    faixa,
    resolucao,
    periodicidade,
    equipamentos,
    pontos
):
    PLANOS.append({
        "tipo": tipo,
        "nome": nome,
        "faixa": faixa,
        "resolucao": resolucao,
        "periodicidade": periodicidade,
        "equipamentos": equipamentos,
        "pontos": pontos
    })


def numerico(
    ordem,
    nominal,
    tolerancia,
    unidade=None,
    descricao=None,
    ordem_original=None
):
    return {
        "ordem": ordem,
        "ordem_original": ordem_original or str(ordem),
        "tipo_ponto": "NUMERICO",
        "descricao": descricao,
        "valor_nominal": nominal,
        "unidade": unidade,
        "tolerancia_inferior": -abs(tolerancia),
        "tolerancia_superior": abs(tolerancia),
        "entrada_tipo": "NUMERICA"
    }


def qualitativo(
    ordem,
    descricao,
    criterio=None,
    ordem_original=None
):
    return {
        "ordem": ordem,
        "ordem_original": ordem_original or str(ordem),
        "tipo_ponto": "QUALITATIVO",
        "descricao": descricao,
        "criterio": criterio,
        "entrada_tipo": "TEXTO"
    }


def funcional(
    ordem,
    descricao,
    criterio,
    ordem_original=None
):
    return {
        "ordem": ordem,
        "ordem_original": ordem_original or str(ordem),
        "tipo_ponto": "FUNCIONAL",
        "descricao": descricao,
        "criterio": criterio,
        "entrada_tipo": "SELECAO"
    }


def criterio_minimo(
    ordem,
    descricao,
    minimo,
    unidade=None
):
    return {
        "ordem": ordem,
        "ordem_original": str(ordem),
        "tipo_ponto": "NUMERICO_MINIMO",
        "descricao": descricao,
        "unidade": unidade,
        "valor_minimo": minimo,
        "criterio": f"Mínimo: {minimo} {unidade or ''}".strip(),
        "entrada_tipo": "NUMERICA"
    }


# ============================================================
# PAQUÍMETROS
# ============================================================

def criar_planos_paquímetro():

    base_300 = [
        qualitativo(1, "Face Externa"),

        numerico(2, 0, 0.05),
        numerico(3, 1.1, 0.05),
        numerico(4, 60, 0.05),
        numerico(5, 120, 0.05),
        numerico(6, 180, 0.05),
        numerico(7, 240, 0.05),
        numerico(8, 300, 0.05),

        qualitativo(9, "Face Interna"),

        numerico(10, 50, 0.05),

        qualitativo(11, "Profundidade"),

        numerico(12, 50, 0.05),

        qualitativo(13, "Ressalto"),

        numerico(14, 50, 0.05)
    ]

    adicionar_plano(
        "Paquímetro",
        "Paquímetro 0-300 padrão",
        "0-300 mm",
        "0,01 mm",
        12,
        ["PAQ-002"],
        base_300
    )

    base_800 = [
        qualitativo(1, "Face Externa"),
        numerico(2, 0, 0.05),
        numerico(3, 1.1, 0.05),
        numerico(4, 160, 0.05),
        numerico(5, 320, 0.05),
        numerico(6, 480, 0.05),
        numerico(7, 640, 0.05),
        numerico(8, 800, 0.05),
        qualitativo(9, "Face Interna"),
        numerico(10, 90, 0.05),
        qualitativo(11, "Inside"),
        numerico(12, 20, 0.05),
        qualitativo(13, "Botões de comando"),
        funcional(14, "Ligado", "Executa função"),
        funcional(15, "Desligado", "Não Exec. função")
    ]

    adicionar_plano(
        "Paquímetro",
        "Paquímetro 0-800",
        "0-800 mm",
        "0,01 mm",
        12,
        ["PAQ-003", "PAQ-009"],
        base_800
    )

    base_500 = [
        qualitativo(1, "Face Externa"),
        numerico(2, 0, 0.05),
        numerico(3, 1.1, 0.05),
        numerico(4, 100, 0.05),
        numerico(5, 200, 0.05),
        numerico(6, 300, 0.05),
        numerico(7, 400, 0.05),
        numerico(8, 500, 0.05),
        qualitativo(9, "Face Interna"),
        numerico(10, 90, 0.05),
        qualitativo(11, "Inside"),
        numerico(12, 20, 0.05),
        qualitativo(13, "Botões de comando"),
        funcional(14, "Ligado", "Executa função"),
        funcional(15, "Desligado", "Não Exec. função")
    ]

    adicionar_plano(
        "Paquímetro",
        "Paquímetro 0-500",
        "0-500 mm",
        "0,01 mm",
        12,
        [
            "PAQ-004",
            "PAQ-005",
            "PAQ-006",
            "PAQ-014",
            "PAQ-016",
            "PAQ-017"
        ],
        base_500
    )

    base_300_funcional = base_300 + [
        qualitativo(15, "Botões de comando"),
        funcional(16, "Ligado", "Executa função"),
        funcional(17, "Desligado", "Não Exec. função")
    ]

    adicionar_plano(
        "Paquímetro",
        "Paquímetro 0-300 com teste funcional",
        "0-300 mm",
        "0,01 mm",
        12,
        ["PAQ-010", "PAQ-011", "PAQ-015"],
        base_300_funcional
    )

    base_150 = [
        qualitativo(1, "Face Externa"),
        numerico(2, 0, 0.05),
        numerico(3, 1.1, 0.05),
        numerico(4, 30, 0.05),
        numerico(5, 60, 0.05),
        numerico(6, 90, 0.05),
        numerico(7, 120, 0.05),
        numerico(8, 150, 0.05),
        qualitativo(9, "Face Interna"),
        numerico(10, 50, 0.05),
        qualitativo(11, "Profundidade"),
        numerico(12, 50, 0.05),
        qualitativo(13, "Ressalto"),
        numerico(14, 50, 0.05),
        qualitativo(15, "Botões de comando"),
        funcional(16, "Ligado", "Executa função"),
        funcional(17, "Desligado", "Não Exec. função")
    ]

    adicionar_plano(
        "Paquímetro",
        "Paquímetro 0-150",
        "0-150 mm",
        "0,01 mm",
        12,
        ["PAQ-012", "PAQ-013"],
        base_150
    )


# ============================================================
# MICRÔMETROS
# ============================================================

def criar_planos_micrometro():

    valores = [
        0,
        2.5,
        5.1,
        7.7,
        10.3,
        12.9,
        15,
        17.6,
        20.2,
        22.8,
        25
    ]

    pontos = [
        numerico(i + 1, valor, 0.007)
        for i, valor in enumerate(valores)
    ]

    pontos.extend([
        qualitativo(
            12,
            "Planeza",
            "Máximo 2 µm"
        ),
        qualitativo(
            13,
            "Paralelismo",
            "Máximo 2 µm"
        ),
        funcional(
            14,
            "Ligado",
            "Executa função"
        ),
        funcional(
            15,
            "Desligado",
            "Não Exec. função"
        )
    ])

    adicionar_plano(
        "Micrômetro",
        "Micrômetro 0-25 resolução 0,01",
        "0-25 mm",
        "0,01 mm",
        12,
        ["MIC-001", "MIC-004", "MIC-005"],
        pontos
    )

    adicionar_plano(
        "Micrômetro",
        "Micrômetro 0-25 resolução 0,001",
        "0-25 mm",
        "0,001 mm",
        12,
        [
            "MIC-003",
            "MIC-006",
            "MIC-007",
            "MIC-008",
            "MIC-009",
            "MIC-010",
            "MIC-011",
            "MIC-012",
            "MIC-013",
            "MIC-014"
        ],
        pontos
    )


# ============================================================
# TRENAS
# ============================================================

def criar_planos_trena():

    pontos = [
        numerico(1, 300, 0.5, "mm"),
        numerico(2, 900, 0.5, "mm"),
        numerico(3, 1500, 0.5, "mm"),
        numerico(4, 2100, 0.5, "mm"),
        numerico(5, 2700, 0.5, "mm"),
        qualitativo(6, "Escala sem avarias"),
        qualitativo(7, "Abertura da trena"),
        qualitativo(8, "Trava da trena"),
        qualitativo(9, "Aspecto geral")
    ]

    grupos = [
        (
            "Trena 3000",
            "3000 mm",
            [
                "TRE-037", "TRE-111", "TRE-129", "TRE-130",
                "TRE-152", "TRE-155", "TRE-169", "TRE-170",
                "TRE-171", "TRE-172", "TRE-191", "TRE-192",
                "TRE-196", "TRE-197", "TRE-198", "TRE-199"
            ]
        ),
        (
            "Trena sem faixa informada",
            None,
            [
                "TRE-052", "TRE-132", "TRE-137",
                "TRE-141", "TRE-143", "TRE-154", "TRE-156"
            ]
        ),
        (
            "Trena 3500",
            "3500 mm",
            [
                "TRE-101", "TRE-113", "TRE-116", "TRE-120",
                "TRE-140", "TRE-142", "TRE-147", "TRE-148",
                "TRE-149", "TRE-150", "TRE-160", "TRE-161",
                "TRE-162", "TRE-163", "TRE-164", "TRE-165",
                "TRE-193", "TRE-195"
            ]
        ),
        (
            "Trena 5000",
            "5000 mm",
            [
                "TRE-136", "TRE-138", "TRE-144", "TRE-151",
                "TRE-153", "TRE-166", "TRE-167", "TRE-168",
                "TRE-174", "TRE-175", "TRE-176", "TRE-177",
                "TRE-178", "TRE-181", "TRE-182", "TRE-183",
                "TRE-184", "TRE-185", "TRE-186", "TRE-187",
                "TRE-188", "TRE-189", "TRE-190", "TRE-194",
                "TRE-201", "TRE-202", "TRE-203", "TRE-204",
                "TRE-205", "TRE-206", "TRE-207", "TRE-208",
                "TRE-209", "TRE-210", "TRE-211", "TRE-212",
                "TRE-213", "TRE-214", "TRE-215", "TRE-216",
                "TRE-217", "TRE-218", "TRE-219", "TRE-220",
                "TRE-221", "TRE-222", "TRE-223", "TRE-224",
                "TRE-225", "TRE-226", "TRE-227", "TRE-228",
                "TRE-229", "TRE-230", "TRE-231", "TRE-232",
                "TRE-233"
            ]
        ),
        (
            "Trena 8000",
            "8000 mm",
            [
                "TRE-158", "TRE-159", "TRE-179", "TRE-200"
            ]
        ),
        (
            "Trena 3500 resolução 5000",
            "3500 mm",
            [
                "TRE-173", "TRE-180"
            ]
        )
    ]

    for nome, faixa, equipamentos in grupos:
        adicionar_plano(
            "Trena",
            nome,
            faixa,
            "1 mm",
            3,
            equipamentos,
            pontos
        )


# ============================================================
# OUTROS INSTRUMENTOS
# ============================================================

def criar_outros_planos():

    adicionar_plano(
        "Durômetro",
        "Durômetro DUR-001",
        "HRB/HRC/HR15T/N/HR30T/N/HR45T/N",
        "1",
        12,
        ["DUR-001"],
        [
            qualitativo(1, "1º ponto 67 a 80 HR15T", "±3,0"),
            qualitativo(2, "2º ponto 81 a 87 HR15T", "±3,0"),
            qualitativo(3, "3º ponto 88 a 93 HR15T", "±3,0"),
            qualitativo(4, "1º ponto 10 a 50 HRB", "±4,0"),
            qualitativo(5, "2º ponto 60 a 80 HRB", "±3,0"),
            qualitativo(6, "3º ponto 85 a 100 HRB", "±2,0"),
            qualitativo(7, "1º ponto 10 a 30 HRC", "±1,5"),
            qualitativo(8, "2º ponto 35 a 55 HRC", "±1,5"),
            qualitativo(9, "3º ponto 60 a 70 HRC", "±1,5")
        ]
    )

    adicionar_plano(
        "Extensômetro",
        "Extensômetro EXT-001",
        "50 mm / 25,0-50,0 mm",
        "2% 25mm / 2% 50mm",
        12,
        ["EXT-001"],
        [
            qualitativo(
                1,
                "Dados conforme Certificado de calibração ABNT NBR ISO 9513"
            ),
            qualitativo(
                6,
                "Classificação (Classe)",
                "Classe exigida: 1"
            )
        ]
    )

    adicionar_plano(
        "Máquina de Tração",
        "Máquina de Tração MTR-001",
        "20 tf / 0-20 tf",
        "1 kgf",
        12,
        ["MTR-001"],
        [
            qualitativo(1, "Dados de deslocamento", "Conforme Certificado"),
            qualitativo(6, "Classificação (Classe)", "Classe exigida: B"),
            qualitativo(8, "Dados de força", "Conforme Certificado"),
            qualitativo(12, "Classificação (Classe)", "Classe exigida: 1")
        ]
    )

    adicionar_plano(
        "Máquina de Embutimento",
        "Máquina de Embutimento MEB-001",
        "0-25 mm / espessura 2,0 mm máx.",
        "1,0 mm",
        24,
        ["MEB-001"],
        [
            qualitativo(
                1,
                "Dados conforme Certificado de calibração"
            )
        ]
    )

    adicionar_plano(
        "Régua graduada",
        "Régua graduada ESC-001",
        "0-1000 mm",
        "1,0 mm",
        36,
        ["ESC-001"],
        [
            *[
                numerico(i + 1, i * 100, 0.4, "mm")
                for i in range(11)
            ],
            qualitativo(12, "Isento de deformações"),
            qualitativo(13, "Graduação legível")
        ]
    )

    adicionar_plano(
        "Régua graduada para furos",
        "ESC-004",
        "0-15 mm",
        "0,1 mm",
        36,
        ["ESC-004"],
        [
            numerico(1, 4, 0.1, "mm"),
            numerico(2, 5.5, 0.1, "mm"),
            numerico(3, 7, 0.1, "mm"),
            numerico(4, 8.5, 0.1, "mm"),
            numerico(5, 10, 0.1, "mm"),
            qualitativo(6, "Isento de deformações"),
            qualitativo(7, "Graduação legível"),
            *[
                numerico(i, None, 0.1, "mm")
                for i in range(8, 18)
            ]
        ]
    )

    adicionar_plano(
        "Régua graduada para furos",
        "ESC-005 / ESC-006",
        "1-15 mm",
        "0,1 mm",
        36,
        ["ESC-005", "ESC-006"],
        [
            *[
                numerico(i, i, 0.1, "mm")
                for i in range(1, 16)
            ],
            qualitativo(16, "Isento de deformações"),
            qualitativo(17, "Graduação legível")
        ]
    )

    adicionar_plano(
        "Régua graduada para furos",
        "ESC-008 / ESC-009 / ESC-010",
        "1-15 mm",
        "0,1 mm",
        36,
        ["ESC-008", "ESC-009", "ESC-010"],
        [
            numerico(1, 1, 0.1, "mm"),
            numerico(2, 2, 0.1, "mm"),
            numerico(3, 4, 0.1, "mm"),
            numerico(4, 5, 0.1, "mm"),
            numerico(5, 6, 0.1, "mm"),
            numerico(6, 7, 0.1, "mm"),
            numerico(7, 8, 0.1, "mm"),
            numerico(8, 9, 0.1, "mm"),
            numerico(9, 10, 0.1, "mm"),
            numerico(10, 11, 0.1, "mm"),
            numerico(11, 12, 0.1, "mm"),
            numerico(12, 13, 0.1, "mm"),
            numerico(13, 14, 0.1, "mm"),
            numerico(14, 15, 0.1, "mm"),
            qualitativo(15, "Isento de deformações"),
            qualitativo(16, "Graduação legível")
        ]
    )


# ============================================================
# GONIÔMETROS
# ============================================================

def criar_goniometros():

    adicionar_plano(
        "Goniômetro",
        "GON-001",
        "0-360°",
        "05'",
        12,
        ["GON-001"],
        [
            numerico(1, 0, 0.25, "°"),
            numerico(2, 31, 0.25, "°"),
            numerico(3, 60, 0.25, "°"),
            numerico(4, 90, 0.25, "°"),
            numerico(5, 60, 0.25, "°"),
            numerico(6, 31, 0.25, "°"),
            numerico(7, 0, 0.25, "°"),
            numerico(8, 30, 0.25, "°"),
            numerico(9, 60, 0.25, "°"),
            numerico(10, 90, 0.25, "°"),
            numerico(11, 60, 0.25, "°"),
            numerico(12, 30, 0.25, "°"),
            qualitativo(16, "Isento de deformações"),
            qualitativo(17, "Graduação legível")
        ]
    )

    adicionar_plano(
        "Goniômetro",
        "GON-002",
        "0-360°",
        "05'",
        12,
        ["GON-002"],
        [
            numerico(i + 1, valor, 0.25, "°")
            for i, valor in enumerate(
                [0, 15, 30, 45, 60, 90, 0, 90, 0, 90, 0, 30]
            )
        ] + [
            qualitativo(16, "Isento de deformações"),
            qualitativo(17, "Graduação legível")
        ]
    )

    adicionar_plano(
        "Goniômetro",
        "GON-004",
        "0-360°",
        "05'",
        12,
        ["GON-004"],
        [
            numerico(1, 0, 0.25, "°", "Q1/4"),
            numerico(2, 15, 0.25, "°", "Q1"),
            numerico(3, 30, 0.25, "°", "Q1"),
            numerico(4, 45, 0.25, "°", "Q1"),
            numerico(5, 60, 0.25, "°", "Q1"),
            numerico(6, 90, 0.25, "°", "Q1"),
            numerico(7, 0, 0.25, "°", "Q2"),
            numerico(8, 90, 0.25, "°", "Q2"),
            numerico(9, 0, 0.25, "°", "Q3"),
            numerico(10, 90, 0.25, "°", "Q3"),
            numerico(11, 0, 0.25, "°", "Q4"),
            numerico(12, 30, 0.25, "°", "Q4"),
            qualitativo(16, "Isento de deformações"),
            qualitativo(17, "Graduação legível")
        ]
    )


# ============================================================
# BALANÇAS
# ============================================================

def criar_balancas():

    pontos_10t = [
        qualitativo(1, "Excentricidade", "Diferença entre 5 pontos ±2,0"),
        numerico(2, 2000, 2.0, "kg"),
        numerico(3, 4000, 2.0, "kg"),
        numerico(4, 6000, 2.0, "kg"),
        numerico(5, 8000, 2.0, "kg"),
        numerico(6, 2000, 2.0, "kg", "Após ajuste"),
        numerico(7, 4000, 2.0, "kg", "Após ajuste"),
        numerico(8, 6000, 2.0, "kg", "Após ajuste"),
        numerico(9, 8000, 2.0, "kg", "Após ajuste"),
        qualitativo(10, "Painel sem defeitos"),
        qualitativo(11, "Teclas sem defeito")
    ]

    adicionar_plano(
        "Balança",
        "Balança 10.000 kg",
        "máx. 10.000 kg / mín. 20 kg",
        "d=1 / e=1 / n=10.000",
        12,
        ["BAL-002", "BAL-004"],
        pontos_10t
    )

    pontos_20t = [
        qualitativo(1, "Excentricidade", "N/A"),
        numerico(2, 2000, 10, "kg"),
        numerico(3, 4000, 10, "kg"),
        numerico(4, 6000, 10, "kg"),
        numerico(5, 8000, 10, "kg"),
        numerico(6, 2000, 10, "kg", "Após ajuste"),
        numerico(7, 4000, 10, "kg", "Após ajuste"),
        numerico(8, 6000, 10, "kg", "Após ajuste"),
        numerico(9, 8000, 10, "kg", "Após ajuste"),
        qualitativo(10, "Painel sem defeitos"),
        qualitativo(11, "Teclas sem defeito")
    ]

    adicionar_plano(
        "Balança",
        "Balança 20.000 kg",
        "máx. 20.000 kg / mín. 100 kg",
        "d=5 / e=5 / n=4.000",
        12,
        ["BAL-003"],
        pontos_20t
    )

    adicionar_plano(
        "Balança Suspensa",
        "Balança Suspensa ULD-20000",
        "máx. 20.000 kg / mín. 100 kg",
        "d=5 / e=5 / n=4.000",
        12,
        ["BAL-005"],
        pontos_20t
    )


# ============================================================
# LÂMINAS DE FOLGA
# ============================================================

def criar_laminas():

    valores = [
        (0.02, 0.005),
        (0.03, 0.005),
        (0.04, 0.005),
        (0.05, 0.005),
        (0.06, 0.010),
        (0.07, 0.010),
        (0.08, 0.010),
        (0.09, 0.010),
        (0.10, 0.010),
        (0.15, 0.010),
        (0.20, 0.010),
        (0.25, 0.020),
        (0.30, 0.020),
        (0.40, 0.020),
        (0.50, 0.020),
        (0.75, 0.020),
        (1.00, 0.020)
    ]

    pontos = [
        numerico(
            i + 1,
            nominal,
            tolerancia,
            "mm"
        )
        for i, (nominal, tolerancia) in enumerate(valores)
    ]

    pontos.append(
        qualitativo(
            18,
            "Lâmina sem avarias",
            "OK"
        )
    )

    adicionar_plano(
        "Lâmina de Folga",
        "Lâmina de Folga LAF-010",
        "0,02-1,00 mm",
        "N/A",
        6,
        ["LAF-010"],
        pontos
    )

    pontos_sem_criterio = pontos[:-1] + [
        qualitativo(18, "Lâmina sem avarias")
    ]

    adicionar_plano(
        "Lâmina de Folga",
        "Lâmina de Folga LAF-011/012/013/014",
        "0,02-1,00 mm",
        "N/A",
        6,
        ["LAF-011", "LAF-012", "LAF-013", "LAF-014"],
        pontos_sem_criterio
    )


# ============================================================
# MANÔMETROS
# ============================================================

def criar_manometros():

    def pontos_manometro(valores, tolerancia):
        return [
            *[
                numerico(
                    i + 1,
                    valor,
                    tolerancia,
                    "kgf/cm²"
                )
                for i, valor in enumerate(valores)
            ],
            qualitativo(len(valores) + 1, "Escala legível"),
            qualitativo(len(valores) + 2, "Visor"),
            qualitativo(len(valores) + 3, "Corpo")
        ]

    adicionar_plano(
        "Manômetro",
        "Manômetro 0-20 kgf/cm²",
        "0-20 kgf/cm²",
        "0,5",
        24,
        ["MN-001", "MN-006"],
        pontos_manometro([0, 5, 10, 15, 20], 1.0)
    )

    adicionar_plano(
        "Manômetro",
        "Manômetro 0-14 grupo 1",
        "0-14 kgf/cm²",
        "0,2",
        24,
        ["MN-004", "MAN-004"],
        pontos_manometro([0, 2, 6, 10, 14], 0.7)
    )

    adicionar_plano(
        "Manômetro",
        "Manômetro 0-14 grupo 2",
        "0-14 kgf/cm²",
        "0,2",
        24,
        ["MN-005", "MAN-005", "MAN-006"],
        pontos_manometro([0, 4, 7, 10, 14], 0.7)
    )


# ============================================================
# VÁLVULAS
# ============================================================

def criar_valvulas():

    pontos = [
        qualitativo(1, "Abertura inicial"),
        numerico(2, 8, 0.5, "bar", "Abertura inicial"),
        qualitativo(3, "Abertura total"),
        numerico(4, 8, 0.5, "bar", "Abertura total"),
        qualitativo(5, "Fechamento"),
        numerico(6, 8, 0.5, "bar", "Fechamento"),
        qualitativo(7, "Limpeza"),
        qualitativo(8, "Lubrificação"),
        qualitativo(9, "Corpo sem avarias")
    ]

    adicionar_plano(
        "Válvula de segurança",
        "Válvula VS",
        "7,5 bar",
        None,
        24,
        ["VS-001", "VS-002"],
        pontos
    )

    adicionar_plano(
        "Válvula de segurança",
        "Válvula VLV",
        None,
        None,
        24,
        ["VLV-001", "VLV-002"],
        pontos
    )


# ============================================================
# TRAÇADOR / MEDIDORES / MÁQUINAS
# ============================================================

def criar_demais():

    adicionar_plano(
        "Traçador de Altura",
        "Traçador TRA-001",
        "0-300 mm",
        "0,01 mm",
        12,
        ["TRA-001"],
        [
            qualitativo(1, "Movimento livre"),
            qualitativo(2, "Contador superior"),
            qualitativo(3, "Contador inferior"),
            qualitativo(4, "Movimento do relógio")
        ]
    )

    adicionar_plano(
        "Medidor de espessura",
        "Medidor MES-001",
        None,
        "0,01 mm",
        None,
        ["MES-001"],
        [
            qualitativo(1, "Movimento livre"),
            qualitativo(2, "Funções do relógio")
        ]
    )

    adicionar_plano(
        "Medidor de espessura",
        "Medidor MES-002",
        "0-25,4 mm",
        "0,01 mm",
        None,
        ["MES-002"],
        [
            qualitativo(1, "Movimento livre"),
            qualitativo(2, "Funções do relógio")
        ]
    )

    adicionar_plano(
        "Medidor de espessura",
        "Medidor MES-003",
        "0-20,0 mm",
        "0,01 mm",
        None,
        ["MES-003"],
        [
            qualitativo(1, "Movimento livre"),
            qualitativo(2, "Funções do relógio")
        ]
    )

    adicionar_plano(
        "Máquina de arquear",
        "Máquina de arquear MA-06",
        None,
        None,
        4,
        ["MA-06"],
        [
            qualitativo(i, f"Ponto {i}")
            for i in range(2, 8)
        ]
    )

    pontos_ma = [
        criterio_minimo(
            1,
            "Resistência à tração do nó",
            628,
            "MPa"
        ),
        *[
            qualitativo(i, f"Ponto {i}")
            for i in range(2, 6)
        ]
    ]

    adicionar_plano(
        "Máquina de arquear",
        "Máquina de arquear MA-09",
        None,
        None,
        4,
        ["MA-09"],
        pontos_ma
    )

    adicionar_plano(
        "Máquina de arquear",
        "Máquina de arquear MA-11",
        None,
        None,
        4,
        ["MA-11"],
        pontos_ma
    )

    adicionar_plano(
        "Máquina de arquear",
        "Máquina de arquear MA-12",
        None,
        None,
        4,
        ["MA-12"],
        [
            criterio_minimo(
                1,
                "Resistência à tração do nó",
                628,
                "MPa"
            ),
            qualitativo(2, "Ponto 2"),
            qualitativo(3, "Ponto 3")
        ]
    )


# ============================================================
# CONSTRUÇÃO DOS DADOS
# ============================================================

def construir_dados():

    PLANOS.clear()

    criar_planos_paquímetro()
    criar_planos_micrometro()
    criar_planos_trena()
    criar_outros_planos()
    criar_goniometros()
    criar_balancas()
    criar_laminas()
    criar_manometros()
    criar_valvulas()
    criar_demais()


# ============================================================
# IMPORTAÇÃO
# ============================================================

def obter_ou_criar_tipo(conexao, nome):

    cursor = conexao.execute(
        """
        SELECT id
        FROM tipos_instrumento
        WHERE nome = ?
        """,
        (nome,)
    )

    resultado = cursor.fetchone()

    if resultado:
        return resultado["id"]

    cursor = conexao.execute(
        """
        INSERT INTO tipos_instrumento
            (nome)
        VALUES
            (?)
        """,
        (nome,)
    )

    return cursor.lastrowid


def obter_ou_criar_plano(conexao, dados, tipo_id):

    cursor = conexao.execute(
        """
        SELECT id
        FROM planos_calibracao
        WHERE nome = ?
        """,
        (dados["nome"],)
    )

    resultado = cursor.fetchone()

    if resultado:
        return resultado["id"]

    cursor = conexao.execute(
        """
        INSERT INTO planos_calibracao (
            tipo_instrumento_id,
            nome,
            faixa,
            resolucao,
            periodicidade_meses
        )
        VALUES (?, ?, ?, ?, ?)
        """,
        (
            tipo_id,
            dados["nome"],
            dados["faixa"],
            dados["resolucao"],
            dados["periodicidade"]
        )
    )

    return cursor.lastrowid


def inserir_pontos(conexao, plano_id, pontos):

    existentes = conexao.execute(
        """
        SELECT COUNT(*) AS quantidade
        FROM pontos_plano
        WHERE plano_id = ?
        """,
        (plano_id,)
    ).fetchone()["quantidade"]

    if existentes > 0:
        return

    for ponto in pontos:

        conexao.execute(
            """
            INSERT INTO pontos_plano (
                plano_id,
                ordem,
                ordem_original,
                tipo_ponto,
                descricao,
                valor_nominal,
                unidade,
                tolerancia_inferior,
                tolerancia_superior,
                criterio,
                valor_minimo,
                valor_maximo,
                classe_exigida,
                entrada_tipo
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                plano_id,
                ponto.get("ordem"),
                ponto.get("ordem_original"),
                ponto.get("tipo_ponto"),
                ponto.get("descricao"),
                ponto.get("valor_nominal"),
                ponto.get("unidade"),
                ponto.get("tolerancia_inferior"),
                ponto.get("tolerancia_superior"),
                ponto.get("criterio"),
                ponto.get("valor_minimo"),
                ponto.get("valor_maximo"),
                ponto.get("classe_exigida"),
                ponto.get("entrada_tipo", "NUMERICA")
            )
        )


def inserir_equipamento(
    conexao,
    codigo,
    tipo_id,
    plano_id,
    dados
):

    existente = conexao.execute(
        """
        SELECT id
        FROM equipamentos
        WHERE codigo = ?
        """,
        (codigo,)
    ).fetchone()

    if existente:

        conexao.execute(
            """
            UPDATE equipamentos

            SET
                tipo_instrumento_id = ?,
                plano_id = ?,
                faixa = ?,
                resolucao = ?,
                periodicidade_meses = ?

            WHERE codigo = ?
            """,
            (
                tipo_id,
                plano_id,
                dados["faixa"],
                dados["resolucao"],
                dados["periodicidade"],
                codigo
            )
        )

        return existente["id"]

    cursor = conexao.execute(
        """
        INSERT INTO equipamentos (
            codigo,
            tipo_instrumento_id,
            plano_id,
            descricao,
            faixa,
            resolucao,
            periodicidade_meses,
            status
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, 'Ativo')
        """,
        (
            codigo,
            tipo_id,
            plano_id,
            dados["tipo"],
            dados["faixa"],
            dados["resolucao"],
            dados["periodicidade"]
        )
    )

    return cursor.lastrowid


def importar():

    criar_banco()
    construir_dados()

    conexao = conectar()

    total_planos = 0
    total_equipamentos = 0
    total_pontos = 0

    try:

        for dados in PLANOS:

            tipo_id = obter_ou_criar_tipo(
                conexao,
                dados["tipo"]
            )

            plano_id = obter_ou_criar_plano(
                conexao,
                dados,
                tipo_id
            )

            inserir_pontos(
                conexao,
                plano_id,
                dados["pontos"]
            )

            total_planos += 1

            for codigo in dados["equipamentos"]:

                inserir_equipamento(
                    conexao,
                    codigo,
                    tipo_id,
                    plano_id,
                    {
                        "tipo": dados["tipo"],
                        "faixa": dados["faixa"],
                        "resolucao": dados["resolucao"],
                        "periodicidade": dados["periodicidade"]
                    }
                )

                total_equipamentos += 1

            total_pontos += len(dados["pontos"])

        conexao.commit()

    except Exception:
        conexao.rollback()
        raise

    finally:
        conexao.close()

    print()
    print("=" * 60)
    print("IMPORTAÇÃO CONCLUÍDA")
    print("=" * 60)
    print(f"Planos processados:       {total_planos}")
    print(f"Equipamentos processados: {total_equipamentos}")
    print(f"Pontos processados:       {total_pontos}")
    print("=" * 60)
    print()
    print(
        "Os dados foram inseridos/atualizados "
        "sem duplicar equipamentos existentes."
    )


# ============================================================
# EXECUÇÃO
# ============================================================

if __name__ == "__main__":
    importar()