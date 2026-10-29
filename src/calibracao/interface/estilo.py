"""Tema e cores — o mesmo padrão visual de todos os programas da MG (ver CLAUDE.md do usuário).

Fundo preto, contornos e títulos brancos; vermelho só no botão principal e em erros/problemas;
amarelo em avisos; verde no que está certo.
"""

import html
import re

from calibracao.regras.avaliacao import Resultado
from calibracao.regras.condicao import Condicao, ParecerFinal
from calibracao.regras.cronograma import Situacao

CORES = {
    "fundo": "#000000", "caixa": "#0a0a0a", "campo": "#161616", "campo_borda": "#3a3a3a",
    "borda": "#e0e0e0", "titulo": "#ffffff", "selecao": "#424242", "botao": "#c62828",
    "botao_mouse": "#e53935", "certo": "#43a047", "aviso": "#ffd54f", "erro": "#ef5350",
}

ESTILO = """
QWidget {{ font-size: 13pt; color: #f0f0f0; font-family: "Segoe UI"; }}
QMainWindow, #central {{ background: {fundo}; }}
QDialog {{ background: {caixa}; }}
QGroupBox {{ font-weight: bold; background: {caixa}; border: 1px solid {borda};
             border-radius: 6px; margin-top: 12px; padding: 8px 8px 4px 8px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {titulo}; }}
QGroupBox QLabel {{ font-weight: normal; }}
QLineEdit, QComboBox, QDateEdit {{ background: {campo}; border: 1px solid {campo_borda};
    border-radius: 4px; padding: 6px; color: #ffffff; selection-background-color: {selecao}; }}
QLineEdit:focus, QComboBox:focus {{ border: 1px solid {borda}; }}
QComboBox QAbstractItemView {{ background: {campo}; selection-background-color: {selecao}; }}
QPushButton {{ background: {campo}; border: 1px solid {borda}; border-radius: 6px; padding: 10px; }}
QPushButton:hover {{ background: {caixa}; }}
QToolTip {{ background: {campo}; color: #f0f0f0; border: 1px solid {borda}; }}
QTabWidget::pane {{ border: 1px solid {borda}; border-radius: 6px; background: {caixa};
                    top: -1px; }}
QTabBar::tab {{ background: {campo}; border: 1px solid {campo_borda}; padding: 8px 22px;
                margin-right: 4px; border-top-left-radius: 6px; border-top-right-radius: 6px; }}
QTabBar::tab:selected {{ background: {caixa}; border: 1px solid {borda}; border-bottom: none;
                         font-weight: bold; color: {titulo}; }}
QTableWidget {{ background: {caixa}; gridline-color: {campo_borda}; border: none;
                selection-background-color: {selecao}; selection-color: #ffffff; }}
QHeaderView::section {{ background: {campo}; color: {titulo}; font-weight: bold; padding: 6px;
                        border: none; border-right: 1px solid {campo_borda};
                        border-bottom: 1px solid {borda}; }}
QTableCornerButton::section {{ background: {campo}; border: none; }}
QTableView::indicator {{ width: 18px; height: 18px; border: 1px solid {borda}; border-radius: 3px;
                         background: {campo}; }}
QTableView::indicator:checked {{ background: {borda}; }}
QScrollBar:vertical {{ background: {caixa}; width: 14px; }}
QScrollBar::handle:vertical {{ background: {campo_borda}; border-radius: 6px; min-height: 30px; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: {caixa}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
#titulo {{ font-size: 22pt; font-weight: bold; letter-spacing: 3px; color: {titulo}; }}
#principal {{ background: {botao}; color: #ffffff; border: none; font-size: 20pt;
              font-weight: bold; letter-spacing: 4px; }}
#principal:hover {{ background: {botao_mouse}; }}
#indicador {{ font-size: 28pt; font-weight: bold; }}
#dica {{ color: #9e9e9e; font-style: italic; }}
#avisos {{ color: {aviso}; }}
#erro {{ color: {erro}; }}
"""

# Faixas coloridas das células (fundo, letra). "Orientação indicativa" imita a etiqueta física da
# MG: letra vermelha sobre fundo amarelo (pedido do usuário em 2026-10-29).
FAIXA_VERDE = ("#1b5e20", "#e8f5e9")
FAIXA_VERMELHA = ("#b71c1c", "#ffebee")
FAIXA_AMARELA = ("#ffd54f", "#000000")
FAIXA_INDICATIVA = ("#ffd54f", "#c62828")
FAIXA_NEUTRA = ("#161616", "#9e9e9e")

FAIXA_INFORMATIVA = ("#424242", "#ffffff")

CORES_SITUACAO = {
    Situacao.VENCIDA: FAIXA_VERMELHA,
    Situacao.PENDENTE_MES: FAIXA_AMARELA,
    Situacao.FEITA_MES: FAIXA_VERDE,
    Situacao.PROXIMO_MES: FAIXA_INFORMATIVA,
    Situacao.EM_DIA: FAIXA_VERDE,
    Situacao.SEM_CALIBRACAO: FAIXA_AMARELA,
    Situacao.SEM_PERIODICIDADE: FAIXA_AMARELA,
}

CORES_RESULTADO = {
    Resultado.APROVADO: FAIXA_VERDE,
    Resultado.REPROVADO: FAIXA_VERMELHA,
    Resultado.NAO_APLICAVEL: FAIXA_NEUTRA,
    Resultado.NAO_INFORMADO: FAIXA_AMARELA,
    Resultado.NAO_AVALIADO: FAIXA_AMARELA,
    Resultado.PENDENTE: FAIXA_AMARELA,
}


# "Orientação indicativa" fica sem cor de fundo: o destaque vem de `aplicar_destaques`.
CORES_PARECER = {
    ParecerFinal.APROVADO: FAIXA_VERDE,
    ParecerFinal.ORIENTACAO_INDICATIVA: None,
    ParecerFinal.REPROVADO_DESATIVADO: FAIXA_VERMELHA,
}

CORES_CONDICAO = {
    Condicao.EM_USO: None,
    Condicao.ORIENTACAO_INDICATIVA: None,
    Condicao.DESATIVADO: FAIXA_NEUTRA,
}


def estilo() -> str:
    return ESTILO.format(**CORES)


_MARCA_INDICATIVA = re.compile("orientação indicativa", re.IGNORECASE)


def tem_orientacao_indicativa(texto: str | None) -> bool:
    return bool(texto and _MARCA_INDICATIVA.search(texto))


def destacar_indicativa(texto: str) -> str:
    """HTML em que só as palavras "orientação indicativa" levam a cor da etiqueta física."""
    fundo, letra = FAIXA_INDICATIVA
    return _MARCA_INDICATIVA.sub(
        lambda achado: f'<span style="background:{fundo}; color:{letra}; font-weight:bold;">'
                       f'&nbsp;{achado.group(0)}&nbsp;</span>',
        html.escape(texto),
    )
