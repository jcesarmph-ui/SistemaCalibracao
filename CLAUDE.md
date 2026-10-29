# Sistema de Calibração (CALIB)

> O padrão geral do usuário (idioma, modo passo a passo, Git, README, arquitetura, **identidade visual
> PySide6**, versão, uso em rede) está em `C:\Users\rodrigo.lima\.claude\CLAUDE.md` e vale aqui também.
> Este arquivo guarda só o que é específico da calibração.

## Objetivo
Sistema da **MG Centro de Serviços** para gestão das calibrações dos instrumentos: cadastro de
equipamentos, tipos, planos e pontos de calibração; registro das calibrações com avaliação por ponto
(considerando a incerteza U); cronograma (vencidas, próximos 30 dias, previstos no mês); gráfico de
tendência; lixeira com exclusão lógica. Detalhes do comportamento atual: `README.md` e
`docs/ATUALIZACAO_LIXEIRA.md`.

## O que o usuário quer (pedido de 2026-10-28)
1. **Trocar Streamlit por PySide6** e gerar o **mesmo tipo de `.exe`** do projeto de classificação
   (`C:\Users\rodrigo.lima\Projetos\Classificação_Automática`). Motivo: o Streamlit precisa abrir um
   servidor local (localhost) e o navegador — pouco prático, instável e ruim para receber atualizações.
2. **Padronizar a interface** com a do programa de classificação (mesmo tema, cores, fontes, logo,
   ícone, layout em faixas, versão na tela) — ver o `CLAUDE.md` do usuário e o código de referência
   `Classificação_Automática/src/classificador/interface/janela.py` e `app.py`.
3. **Melhorias e correções menores** que o usuário vai listar — perguntar a ele quais são, uma por vez.
4. Manter **todas as funcionalidades atuais**. (Os dados do banco atual são de protótipo — ver
   "Planilha DQ05 e dados iniciais" abaixo.)

## Origem e estado atual
- Feito pelo usuário no computador de casa, com ChatGPT. Código completo no GitHub
  (`jcesarmph-ui/SistemaCalibracao`, **público**), clonado aqui em 2026-10-28.
- Stack atual: Streamlit + SQLite + Pandas + Matplotlib; testes com `unittest` (`tests/test_lixeira.py`).
- `main.py` (~2.300 linhas) mistura tela e regras; já separados: `app/database/db.py` (banco e
  migrações), `app/services/calibracao_service.py`, `lixeira_service.py`, `incertezas_referencia.py`,
  `app/interface.py`. `iniciar_calib.py` + `Sistema_de_Calibracao.spec` = lançador do `.exe` atual.
- Regras de avaliação e cores já existentes (manter): ponto numérico aprovado só se a faixa
  `[valor − U, valor + U]` fica dentro dos limites; incerteza ausente → "não avaliado" (nunca tratar U
  como zero; salvar é bloqueado). Verde = aprovado, vermelho = reprovado, amarelo = pendência/restrição,
  cinza = sem avaliação — coerente com o padrão de cores do usuário.

## Planilha DQ05 e dados iniciais (definido pelo usuário em 2026-10-28)
- O CALIB substitui a planilha oficial (grande, lotada e travada):
  "DQ05 Cronograma de calibração de EIMEs", na pasta da Garantia da Qualidade na rede (caminho
  completo na memória local do Claude — não escrever aqui: repositório público). Tem a aba
  "Cronograma de Calibração" + uma aba por equipamento.
- **A planilha é intocável**: só ler, sempre a partir de uma **cópia** na pasta temporária; nunca
  abrir para escrita, nunca salvar por cima, nunca versionar. Conferir com SHA-256 que ficou igual.
- **O programa ainda não é usado — tudo é protótipo.** O banco atual (abaixo) tem dados de teste
  importados de uma versão antiga da planilha, com faltas (ex.: micrômetros sem tolerância, válvulas
  com plano vazio, incertezas divergentes).
- **O que o programa deve ter, igual à planilha:** tudo o que permite fazer **novas** calibrações —
  instrumentos (quantidade e qual é qual: código, tipo, faixa, resolução, fabricante, periodicidade),
  **planos de calibração** (conjunto de pontos de um modelo de instrumento) com os **pontos nominais
  numéricos e qualitativos**, tolerâncias/critérios e demais informações necessárias.
- **Calibrações já feitas NÃO entram no programa.** Ele começa **sem nenhuma calibração** quando for
  implantado; o histórico anterior à implantação fica só na planilha, para consulta.
- **Começa "vazio de inputs"**: nenhuma data de última/próxima calibração vem da planilha; o
  cronograma começa vazio. Transição: nos primeiros meses o usuário olha na planilha quando calibrar
  cada instrumento, registra a calibração no programa e, daí em diante, o programa calcula a próxima.
  Quando todos os instrumentos tiverem sido calibrados ao menos uma vez no programa, a planilha deixa
  de ser acompanhada (só consulta de histórico antigo).
- **Cada instrumento já vem com tudo indicado no plano**: pontos, tolerâncias/critérios **e incerteza
  (U)**. Quando um valor mudou ao longo das calibrações da planilha, vale o da **última calibração**
  (é o atual). Se mudar no futuro, o usuário altera pela tela de edição de planos/pontos (já existe no
  protótipo: "Gerenciar tipos, planos e pontos nominais" — manter na versão PySide6). Hoje cada
  instrumento tem o seu próprio plano.
- **Importar fiel à planilha, sem corrigir nada.** Erros ou valores faltando na planilha não são
  problema do programa: vão como estão (ex.: valor que parece digitado errado; abas sem
  tolerância). Quem confere é o usuário, com análise crítica a cada calibração, corrigindo pela tela de
  edição. Não perguntar sobre "possíveis erros" da planilha — só sobre como **interpretar** um dado.
- **Quais instrumentos entram** (decisão do usuário em 2026-10-28): a lista mestra é a aba
  **"Cronograma de Calibração"**. Ficam de fora: (a) abas de instrumentos que **não estão no
  cronograma** (já desativados); (b) linhas do cronograma **tachadas com fundo vermelho**
  (desativados). Localização em letra vermelha/fundo amarelo (reserva, orientativo) **não** exclui —
  esses entram. Instrumentos do cronograma **sem aba** própria (reserva no laboratório ou não
  calibrados) **entram sem plano**.
  Localização vem do cronograma; o resto do cadastro e o plano vêm da aba do instrumento.
- **O usuário pode fazer tudo pelo programa**: incluir/editar/desativar instrumentos, criar/editar
  planos, incluir/editar/remover pontos (inclusive marcar que um instrumento não precisa de
  calibração). Nada de cadastro pode depender de mexer no banco ou no código.
- Leitura: considerar o `number_format` da célula (ex.: `0.007` com formato `"± "0.000` = ± 0,007).
  "Classificação (Classe)" com valor `1` (extensômetro, máquina de tração) = **classe exigida 1**, não tolerância.

## Bancos de dados — CUIDADO
- **Banco do protótipo**:
  `C:\Users\rodrigo.lima\Projetos\Calibração de Instrumentos\Arquivos\data\calibracao.db`
  (pasta do programa protótipo: `Calibração de Instrumentos.exe` + `Arquivos\`).
- **Nunca alterar esse banco** nem a pasta `Calibração de Instrumentos`. Para desenvolver, **copiar** o
  banco para `data/calibracao.db` desta pasta (ignorado pelo Git: `data/*.db`) e trabalhar na cópia.
- Na entrega (`1.0.0`), vai para a pasta comum da empresa um banco **novo**, montado a partir da
  planilha (cadastros e planos, sem calibrações), junto do `.exe` novo.
- O `.db` **nunca** esteve no GitHub (conferido em todo o histórico em 2026-10-28).

## Pendência de confidencialidade (lembrar; resolver só quando o usuário pedir)
O repositório é público e contém informação da empresa:
- `scripts/importar.dados.reais.py`: planos de calibração reais (códigos PAQ-002, MIC-001, DUR-001…,
  pontos nominais, tolerâncias).
- `docs/auditoria_lixeira.json`: estrutura do banco e quantidade de registros (sem os dados em si).

Opções para o usuário decidir: **(a)** tornar o repositório **privado**; ou **(b)** manter público e
remover esses dados **também do histórico** (reescrita de histórico + force push — explicar o que
isso significa e pedir confirmação explícita antes). Não decidir sozinho.
Isso faz parte do objetivo futuro "GitHub como vitrine, sem nada da empresa" (ver `CLAUDE.md` do
usuário): o usuário quer fazer **depois, não agora** — apenas lembrar a pendência, sem executar.

## Limpeza a propor (perguntar antes de apagar qualquer coisa)
`__pycache__/` versionado; `main_backup_antes_visual.py`; `notepad adicionar_responsavel.py`; arquivo
vazio `streamlit`; scripts de uso único (`corrigir_datas.py`, `adicionar_responsavel.py`);
`Abrir_CALIB.bat` e `iniciar_calib.py` (deixam de existir sem Streamlit); `.vscode/`.

## Onde paramos (2026-10-28, fim do dia)
- Fase 0 concluída (PR #1 juntado ao `main`). Fase 1 (importador) pronta na branch
  `fase-1-importador` (já enviada ao GitHub; **PR ainda não aberto**). Versão `0.1.0`.
- Banco novo gerado em `dados/calibracao.db` + `dados/conferencia_importacao.xlsx` (fora do Git):
  123 instrumentos (100 com plano, 23 sem), 987 pontos, 74 fora; planilha original conferida intacta.
- **Próximos passos (amanhã):** (1) usuário confere a planilha de conferência
  (`! start dados/conferencia_importacao.xlsx`) e aprova ou pede ajustes; (2) abrir o PR da fase 1 e
  atualizar o README; (3) fase 2 — perguntar como avaliar os pontos sem nominal fixo (9 do DUR-001
  e "Diferença entre 5 pontos" de BAL-002/BAL-004).
- Pendente: `.gitattributes` (avisos LF/CRLF), copiando do projeto de classificação.
- 2026-10-29: usuário **aprovou** a conferência da importação. Pontos sem U no banco novo (fiel à
  planilha): 148 numéricos (25 trenas, MIC-015, PAQ-013, ESC-006, 1 de ESC-005, 1 de LAF-017) e 21
  limites (Planeza/Paralelismo dos micrômetros, nó de MA-09/11/12) — a U é informada na edição do plano
  ou ao registrar. Classe e verificação visual não usam U.
- **Regra para a fase 2 (decidida em 2026-10-29):** ponto de **Limite** segue a mesma lógica do
  numérico — máximo: aprovado se `medido + U ≤ máximo`; mínimo: aprovado se `medido − U ≥ mínimo`;
  sem U → "não avaliado" (salvar bloqueado).
- **Pontos numéricos sem nominal fixo (decidido em 2026-10-29)** — DUR-001 (faixas "67 a 80 HR15T"…) e
  "Diferença entre 5 pontos" das balanças: calibração feita por **laboratório externo**, que entrega o
  certificado. O usuário digita o **erro/desvio** (ou a diferença) e a **U** do certificado; aprovado se
  `erro ± U` fica dentro da tolerância. Campos opcionais de valor do padrão/medido só para registro.
  **U negativa** na planilha (ex.: −0,36 no DUR-001) é usada **sem o sinal** (|U|), como no protótipo.
- **Pontos de Classe (decidido em 2026-10-29)** — EXT-001 e MTR-001: o usuário escolhe
  **Aprovado/Reprovado** olhando o certificado; o programa só mostra a classe exigida ao lado.
- **Resultado geral (decidido em 2026-10-29):** algum reprovado → Reprovado; algum "orientação
  indicativa" → **"Aprovado como orientação indicativa"** (nome usado na MG para o "aprovado com
  restrição" do protótipo — usar esse texto no programa); senão Aprovado. **Todo ponto precisa ser
  preenchido** para salvar (ponto em branco nunca é ignorado, diferente do protótipo); se não se aplica
  naquela vez, o usuário marca **"Não aplicável" com motivo** e o ponto não conta.
- Na tela, escrever **"Incerteza (U)"** por extenso, com tooltip explicando (o usuário não conhecia
  a sigla "U").

## Programa novo × protótipo (decisão do usuário em 2026-10-28)
- O programa oficial é **feito do zero** (PySide6), usando o protótipo Streamlit como referência das
  regras e funcionalidades — comparar funcionalidade por funcionalidade antes de dar por pronto.
- **Mesmo repositório** (`SistemaCalibracao`). Durante o desenvolvimento o código novo fica em `src/`,
  ao lado do protótipo; **no final, o GitHub mostra só as pastas do programa final** (o protótipo
  continua no histórico do Git; perguntar antes de remover os arquivos dele).
- **README** deve registrar a história: o protótipo foi feito em Streamlit, o programa final em
  PySide6, e tudo o que mudou/melhorou.

## Plano proposto (cada fase = branch + PR; confirmar com o usuário antes de começar)
0. **Fundação**: limpeza (sem remover nada por confidencialidade — ver pendência); `pyproject.toml` (versão `0.x` a partir de
   `__version__`), `.venv`, pytest + ruff, ADRs em `docs/decisoes/`, `.claude/settings.json`.
1. **Importador da planilha DQ05** → banco novo em `dados/` (instrumentos, planos, pontos,
   tolerâncias/critérios, incerteza da última calibração; **sem calibrações**) + relatório para o
   usuário conferir. Testes com planilha fictícia gerada no próprio teste.
2. **Regras do zero, com testes**, tendo o protótipo como referência: avaliação por ponto com U,
   cronograma (vencidas/próximas 30 dias/mês), lixeira com exclusão lógica.
3. **Banco para uso em rede**: classe repositório; journal tradicional (nunca WAL), `busy_timeout`,
   transações curtas, backup diário automático (padrão do usuário).
4. **Interface PySide6** com o padrão visual: indicadores (Equipamentos, Calibrações, Vencidas,
   Próximas 30 dias) e abas Equipamentos, Cronograma, Lixeira; gráfico de tendência com Matplotlib
   embutido (exportar PNG). Mostrar "fotos" da tela para o usuário aprovar o layout antes de seguir.
5. **Melhorias e correções** listadas pelo usuário.
6. **`.exe` (PyInstaller) + entrega `1.0.0`** na pasta comum da rede, com o banco novo montado da
   planilha (sem calibrações). README com a história protótipo → final; protótipo sai da árvore
   (perguntar antes).

## Perguntas para fazer ao usuário no início (uma por vez)
- (Só lembrar, sem insistir) a pendência de confidencialidade fica para depois, a pedido do usuário.
- Quais melhorias e correções ele já tem em mente?
- Quantas pessoas usam o CALIB e se ficará na mesma pasta comum da rede que o de classificação.
- Se alguma funcionalidade atual pode sair ou mudar na troca para PySide6.
