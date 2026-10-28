# 0001 — Programa oficial feito do zero em PySide6, com o protótipo como referência

- **Data:** 2026-10-28
- **Situação:** aceita

## Contexto
O CALIB foi feito primeiro como **protótipo** em Streamlit + SQLite, para substituir a planilha de
cronograma de calibração (DQ05), que ficou grande, lenta e travando. O protótipo provou as regras
(avaliação por ponto considerando a incerteza U, cronograma, lixeira), mas:

- o Streamlit precisa abrir um servidor local e o navegador — pouco prático e ruim de atualizar;
- tela e regras estão misturadas num arquivo de ~2.300 linhas;
- os planos de calibração foram digitados à mão no código, com faltas (ex.: tolerâncias de
  micrômetros, pontos de válvulas) e desatualizados em relação à planilha;
- o banco carrega código de migração de versões antigas do próprio protótipo.

## Decisão
1. Fazer o programa oficial **do zero**, em **PySide6** (padrão dos programas da empresa), com
   camadas separadas: interface → serviços/regras → dados.
2. Usar o protótipo como **referência** das regras e funcionalidades; antes de concluir, comparar
   funcionalidade por funcionalidade.
3. Os cadastros (instrumentos, planos, pontos, tolerâncias, critérios e incertezas) vêm de um
   **importador da planilha DQ05**, fiel ao que está nela (sem correções — o usuário revisa pela
   tela de edição). As **calibrações já feitas não entram**: o programa começa sem calibrações e o
   histórico anterior fica na planilha.
4. Manter o **mesmo repositório**. O código novo fica em `src/calibracao/`; no fim, o protótipo sai
   da árvore (continua no histórico do Git) e o README registra a evolução protótipo → final.

## Consequências
- O código do protótipo não é reformado; serve de consulta até a entrega da versão `1.0.0`.
- Nenhum dado da empresa fica no código novo: o importador lê a planilha na hora; os testes usam
  uma planilha fictícia.
