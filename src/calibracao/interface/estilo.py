"""Tema e cores — o mesmo padrão visual de todos os programas da MG (ver CLAUDE.md do usuário).

Fundo preto, contornos e títulos brancos; vermelho só no botão principal e em erros/problemas;
amarelo em avisos; verde no que está certo.
"""

import html
import re

from calibracao.interface.marca_check import caminho_do_check
from calibracao.interface.tema_icones import arquivo_do_icone
from calibracao.regras.avaliacao import Resultado
from calibracao.regras.condicao import Condicao, ParecerFinal
from calibracao.regras.cronograma import Situacao, SituacaoNoMes

# Cada cor tem um nome; cada tema é uma tabela com os mesmos nomes (pedido de 2026-11-10: modo
# claro e escuro escolhido pela pessoa). O escuro é o padrão de todos os programas da MG.
ESCURO = {
    "fundo": "#000000", "caixa": "#0a0a0a", "campo": "#161616", "campo_borda": "#3a3a3a",
    "borda": "#e0e0e0", "titulo": "#ffffff", "selecao": "#424242", "botao": "#c62828",
    "botao_mouse": "#e53935",
    # Passar o mouse no que é clicável clareia (pedido de 2026-11-03, item 2 do teste).
    "mouse": "#2e2e2e", "mouse_tabela": "#1e1e1e", "mouse_painel": "#161616",
    "certo": "#43a047", "aviso": "#ffd54f", "erro": "#ef5350", "dentro": "#1b5e20",
    "fora": "#b71c1c",
    "texto": "#f0f0f0", "texto_campo": "#ffffff", "dica": "#9e9e9e", "desativado": "#6e6e6e",
    "desativado_dia": "#5a5a5a", "selecao_texto": "#ffffff", "selecao_linha": "#ffffff",
    "aviso_fundo": "#ffd54f", "neutra_fundo": "#161616", "neutra_letra": "#9e9e9e",
}

# Tema claro: contornos e títulos escuros sobre fundo claro. O amarelo de aviso, como letra, fica
# num âmbar escuro (amarelo-claro sobre branco não se lê); como fundo continua o amarelo.
_CLARO = {
    "botao": "#c62828", "botao_mouse": "#e53935", "certo": "#2e7d32", "aviso": "#8d6e00",
    "erro": "#c62828", "dentro": "#1b5e20", "fora": "#b71c1c", "aviso_fundo": "#ffd54f",
}
# Escolhido pelo usuário por foto em 2026-11-10 (entre cinza, gelo e branco).
CLARO = {
    **_CLARO,
    "fundo": "#c9c9c9", "caixa": "#dedede", "campo": "#f5f5f5", "campo_borda": "#8a8a8a",
    "borda": "#2b2b2b", "titulo": "#111111", "selecao": "#a9a9a9", "mouse": "#cfcfcf",
    "mouse_tabela": "#d2d2d2", "mouse_painel": "#d4d4d4", "texto": "#141414",
    "texto_campo": "#000000", "dica": "#555555", "desativado": "#8f8f8f",
    "desativado_dia": "#9a9a9a", "selecao_texto": "#000000", "selecao_linha": "#2b2b2b",
    "neutra_fundo": "#bdbdbd", "neutra_letra": "#424242",
}
TEMAS = {"escuro": ESCURO, "claro": CLARO}

# As telas leem daqui; `aplicar_tema` troca o conteúdo (o mesmo dicionário, então quem já
# importou CORES enxerga a troca). Deve ser chamado antes de montar as janelas.
CORES = dict(ESCURO)
_tema = ["escuro"]


ESTILO = """
QWidget {{ font-size: 13pt; color: {texto}; font-family: "Segoe UI"; }}
QMainWindow, #central, #rolagem_central {{ background: {fundo}; }}
QDialog, QMessageBox {{ background: {caixa}; }}
QMessageBox {{ border: 1px solid {borda}; }}
QGroupBox {{ font-weight: bold; background: {caixa}; border: 1px solid {borda};
             border-radius: 6px; margin-top: 12px; padding: 8px 8px 4px 8px; }}
QGroupBox::title {{ subcontrol-origin: margin; left: 10px; padding: 0 4px; color: {titulo}; }}
QGroupBox QLabel {{ font-weight: normal; }}
QLineEdit, QComboBox, QDateEdit {{ background: {campo}; border: 1px solid {campo_borda};
    border-radius: 4px; padding: 6px; color: {texto_campo}; selection-background-color: {selecao};
    selection-color: {selecao_texto}; }}
QLineEdit:focus, QComboBox:focus {{ border: 1px solid {borda}; }}
QComboBox:hover:enabled {{ background: {mouse}; }}
QComboBox QAbstractItemView {{ background: {campo}; color: {texto};
    selection-background-color: {selecao}; selection-color: {selecao_texto}; }}
QListView#sugestoes {{ background: {campo}; color: {texto}; border: 1px solid {borda};
    selection-background-color: {selecao}; selection-color: {selecao_texto}; outline: none; }}
QListView#sugestoes::item {{ padding: 4px 6px; }}
QListView#sugestoes::item:hover {{ background: {mouse}; }}
QPushButton {{ background: {campo}; border: 1px solid {borda}; border-radius: 6px; padding: 10px; }}
QPushButton:hover:enabled {{ background: {mouse}; color: {texto_campo}; }}
QPushButton:disabled {{ color: {desativado}; border: 1px solid {campo_borda}; }}
/* Campo de data: no lugar da setinha, o ícone de calendário (pedido de 2026-11-10). */
QDateEdit::drop-down {{ subcontrol-origin: padding; subcontrol-position: center right;
    width: 34px; border: none; }}
QDateEdit::down-arrow {{ image: url({calendario}); width: 24px; height: 24px; }}
QToolButton#calendario {{ background: {campo}; border: 1px solid {campo_borda};
    border-radius: 4px; padding: 4px; }}
QToolButton#calendario:hover {{ background: {mouse}; border: 1px solid {borda}; }}
QCalendarWidget QWidget {{ alternate-background-color: {campo}; }}
QCalendarWidget QAbstractItemView {{ background: {campo}; color: {texto};
    selection-background-color: {selecao}; selection-color: {selecao_texto}; outline: none; }}
QCalendarWidget QAbstractItemView:disabled {{ color: {desativado_dia}; }}
QCalendarWidget #qt_calendar_navigationbar {{ background: {caixa};
                                              border-bottom: 1px solid {campo_borda}; }}
QCalendarWidget QToolButton {{ color: {titulo}; background: transparent; padding: 4px 10px;
                               border: none; font-weight: bold; }}
QCalendarWidget QToolButton:hover {{ background: {mouse}; border-radius: 4px; }}
QCalendarWidget QMenu {{ background: {campo}; color: {texto}; }}
QCalendarWidget QMenu::item:selected {{ background: {selecao}; }}
QCalendarWidget QSpinBox {{ background: {campo}; color: {texto_campo};
                            border: 1px solid {campo_borda};
                            selection-background-color: {selecao}; }}
QToolTip {{ background: {campo}; color: {texto}; border: 1px solid {borda}; }}
QTabWidget::pane {{ border: 1px solid {borda}; border-radius: 6px; background: {caixa};
                    top: -1px; }}
QTabBar::tab {{ background: {campo}; border: 1px solid {campo_borda}; padding: 8px 22px;
                margin-right: 4px; border-top-left-radius: 6px; border-top-right-radius: 6px; }}
QTabBar::tab:hover:!selected {{ background: {mouse}; color: {texto_campo}; }}
QTabBar::tab:selected {{ background: {caixa}; border: 1px solid {borda}; border-bottom: none;
                         font-weight: bold; color: {titulo}; }}
QTableWidget {{ background: {caixa}; gridline-color: {campo_borda}; border: none;
                selection-background-color: {selecao}; selection-color: {selecao_texto}; }}
QTableView[clicavel="true"]::item:hover {{ background: {mouse_tabela}; }}
QTableView::item:selected, QTableView::item:selected:!active {{
    background: {selecao}; color: {selecao_texto};
    border-top: 2px solid {selecao_linha}; border-bottom: 2px solid {selecao_linha}; }}
QHeaderView::section {{ background: {campo}; color: {titulo}; font-weight: bold; padding: 6px;
                        border: none; border-right: 1px solid {campo_borda};
                        border-bottom: 1px solid {borda}; }}
QTableCornerButton::section {{ background: {campo}; border: none; }}
QTableView::indicator {{ width: 18px; height: 18px; border: 1px solid {borda}; border-radius: 3px;
                         background: {campo}; }}
QCheckBox::indicator {{ width: 18px; height: 18px; border: 1px solid {borda}; border-radius: 3px;
                       background: {campo}; }}
QTableView::indicator:checked, QCheckBox::indicator:checked {{ image: url({check}); }}
QCheckBox::indicator:hover:enabled, QTableView::indicator:hover {{ background: {mouse}; }}
QCheckBox::indicator:disabled {{ border: 1px solid {campo_borda}; }}
QScrollBar:vertical {{ background: {caixa}; width: 14px; }}
QScrollBar::handle:vertical {{ background: {campo_borda}; border-radius: 6px; min-height: 30px; }}
QScrollBar::add-page:vertical, QScrollBar::sub-page:vertical {{ background: {caixa}; }}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {{ height: 0px; }}
#titulo {{ font-size: 22pt; font-weight: bold; letter-spacing: 3px; color: {titulo}; }}
#principal {{ background: {botao}; color: #ffffff; border: none; font-size: 20pt;
              font-weight: bold; letter-spacing: 4px; }}
#principal:hover {{ background: {botao_mouse}; }}
/* Botão sol/lua do tema: contorno de botão, clareia com o mouse, afunda ao clicar. */
QToolButton#botao_tema {{ background: {campo}; border: 1px solid {borda}; border-radius: 6px;
    padding: 3px; }}
QToolButton#botao_tema:hover {{ background: {mouse}; }}
QToolButton#botao_tema:pressed {{ background: {selecao}; padding: 4px 2px 2px 4px; }}
#indicador {{ font-size: 28pt; font-weight: bold; }}
#dica {{ color: {dica}; font-style: italic; }}
#avisos {{ color: {aviso}; }}
#erro {{ color: {erro}; }}
#modo {{ color: {titulo}; font-size: 10pt; padding: 1px 4px; }}
#canto {{ font-size: 10pt; padding: 2px 12px; border-radius: 4px; }}
RotuloClicavel#modo:hover {{ background: {mouse}; border-radius: 3px; }}
PainelClicavel:hover {{ background: {mouse_painel}; }}
"""

# Faixas coloridas das células (fundo, letra). "Orientação indicativa" imita a etiqueta física da
# MG: letra vermelha sobre fundo amarelo (pedido do usuário em 2026-10-29). "Reserva" fica em
# azul com letra branca (pedido de 2026-10-30).
FAIXA_VERDE = ("#1b5e20", "#e8f5e9")
FAIXA_VERMELHA = ("#b71c1c", "#ffebee")
FAIXA_AMARELA = ("#ffd54f", "#000000")
FAIXA_INDICATIVA = ("#ffd54f", "#c62828")
FAIXA_RESERVA = ("#1565c0", "#ffffff")
FAIXA_NEUTRA = (ESCURO["neutra_fundo"], ESCURO["neutra_letra"])  # muda com o tema

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

# Feita com atraso não é alardeada: "Feita" é sempre verde (pedido do usuário em 2026-10-30).
CORES_SITUACAO_NO_MES = {
    SituacaoNoMes.FEITA: FAIXA_VERDE,
    SituacaoNoMes.PENDENTE: FAIXA_AMARELA,
    SituacaoNoMes.VENCIDA: FAIXA_VERMELHA,
    SituacaoNoMes.PREVISTA: FAIXA_INFORMATIVA,
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
    Condicao.DESATIVADO: FAIXA_NEUTRA,
}


def aplicar_tema(nome: str) -> None:
    """Troca as cores do programa (antes de montar as janelas). Nome desconhecido = escuro."""
    global FAIXA_NEUTRA
    nome = nome if nome in TEMAS else "escuro"
    CORES.clear()
    CORES.update(TEMAS[nome])
    _tema[0] = nome
    antiga, FAIXA_NEUTRA = FAIXA_NEUTRA, (CORES["neutra_fundo"], CORES["neutra_letra"])
    for tabela in (CORES_SITUACAO, CORES_SITUACAO_NO_MES, CORES_RESULTADO, CORES_PARECER,
                   CORES_CONDICAO):
        for chave, faixa in tabela.items():
            if faixa == antiga:
                tabela[chave] = FAIXA_NEUTRA


def tema_atual() -> str:
    return _tema[0]


def tema_claro() -> bool:
    return _tema[0] != "escuro"


def estilo() -> str:
    # Caixinha marcada = contorno com ✓ dentro, na cor dos títulos (pedido de 2026-11-03).
    return ESTILO.format(**CORES, check=caminho_do_check(CORES["titulo"]),
                         calendario=arquivo_do_icone("calendar_month", CORES["titulo"]))


# Palavras que ganham a cor de etiqueta onde aparecerem nas tabelas.
_MARCAS = re.compile(r"orientação indicativa|\breserva\b", re.IGNORECASE)


def tem_destaque(texto: str | None) -> bool:
    return bool(texto and _MARCAS.search(texto))


def abreviar_indicativa(texto: str | None) -> bool:
    """Reserva e orientação indicativa juntas não cabem na coluna: na tela, "Orientação
    indicativa" vira "IND." (pedido de 2026-11-03; o banco guarda por extenso)."""
    marcas = {m.lower() for m in _MARCAS.findall(texto or "")}
    return marcas == {"reserva", "orientação indicativa"}


def destacar(texto: str) -> str:
    """HTML em que só as palavras marcadas levam a cor da etiqueta (indicativa ou reserva)."""
    curto = abreviar_indicativa(texto)

    def pintar(achado: re.Match) -> str:
        reserva = achado.group(0).lower() == "reserva"
        fundo, letra = FAIXA_RESERVA if reserva else FAIXA_INDICATIVA
        palavra = "IND." if curto and not reserva else achado.group(0)
        return (f'<span style="background:{fundo}; color:{letra}; font-weight:bold;">'
                f'&nbsp;{palavra}&nbsp;</span>')
    return _MARCAS.sub(pintar, html.escape(texto))
