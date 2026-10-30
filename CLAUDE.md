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

## Onde paramos (2026-10-30)
- Fases 0–4 juntadas ao `main` (PRs #1–#5). Versão **`0.4.0`**.
- **Fase 5 (melhorias):** PR #6 **juntado** em 2026-10-30, aprovado por foto (botão **"Novo
  plano…"** na ficha, **"Enviar plano para a Lixeira…"** no painel do plano — plano na Lixeira
  continua aparecendo como "(na Lixeira)" —, **pesquisa por texto na Lixeira**).
  Depois: **"Reserva" em azul `#1565c0` com letra branca** (branch `fase-5-reserva-azul`, PR #7),
  nos mesmos lugares da "Orientação indicativa" (aprovado por foto). 221 testes.
  Fotos: `dados/fotos/foto_fase5.py` e `foto_reserva.py` (fora do Git).
  Depois: **corrigir calibração salva** (branch `fase-5-editar-calibracao`): esquema **v5**
  (tabela `correcoes_calibracao`), `Repositorio.corrigir_calibracao`/`listar_correcoes`, botão
  "Corrigir" (janela de registro em modo correção) e caixa "Correções feitas" em "Ver pontos".
  Aprovado por foto. 233 testes. Foto: `dados/fotos/foto_correcao.py`.
  Depois (branch `fase-5-protege-copia`): **proteção contra cópia** — o banco guarda o lugar
  oficial (`metadados.pasta_oficial`, o primeiro de onde é aberto; `dados/local_banco.py`); aberto
  de outro lugar = só consulta + aviso amarelo; clicar no aviso e digitar **MUDAR** torna aquele o
  oficial; sem `calibracao.db` = erro (nunca cria banco vazio; `app.abrir_banco`). **Na entrega
  (fase 6) o banco vai SEM `pasta_oficial`** (apagar a chave se o banco tiver sido aberto aqui pelo
  `app.py`). Também: botões sem "…" e título das janelas só com o código. 240 testes.
  Foto: `dados/fotos/foto_copia.py`.
  Depois (branch `fase-5-cronograma-mes`): **cronograma de qualquer mês** + **custo estimado** +
  **motivo do atraso** — esquema **v6** (`calibracoes.motivo_atraso`,
  `instrumentos.motivo_atraso_pendente`); `regras/cronograma.previstas_no_mes`;
  `Repositorio.cronograma_do_mes`/`informar_motivo_atraso`/`prevista_atual`. Aprovado por foto.
  252 testes. Foto: `dados/fotos/foto_cronograma_mes.py`.
  **Comparação com o protótipo concluída.** Próximo do roteiro: fechar a fase 5 (versão `0.5.0`).
- **Comparação com o protótipo (2026-10-29):**
  1. ~~Editar calibração já salva~~ feito (2026-10-30).
  2. ~~Cronograma de qualquer mês~~ feito (2026-10-30).
  3. Outras melhorias que o usuário tiver ("por agora, nada" em 2026-10-29).
- Já feito na fase 4 (e aprovado por foto): `interface/janela.py` (cabeçalho, painéis do topo
  clicáveis com lista flutuante, aba Cronograma), `componentes.py` (célula, `aplicar_destaques`,
  `PainelClicavel`, `ListaFlutuante`), `estilo.py`, `aba_instrumentos.py` (lista + ficha),
  `painel_plano.py` (pontos editáveis), `app.py`. Localização padronizada (`regras/localizacao.py`,
  aplicada no importador, ao salvar e no banco `dados/calibracao.db` — cópia de antes em
  `dados/calibracao_antes_padronizar_localizacao.db`).
- **Condição + parecer final: feito** (2026-10-29, 2ª sessão): esquema **v3** (tabela `condicoes`
  no lugar de `desativacoes`, com migração; custo de compra/responsável; parecer final, motivo e
  custo da calibração); repositório (`mudar_condicao`, `condicao_atual`, `historico_condicao`,
  `condicoes_atuais`; parecer obrigatório muda a condição; calibração na Lixeira desfaz a mudança);
  tela (filtros Condição/Tipo/Localização, colunas Código | Localização | Condição | Desde |
  Situação, custo e responsável na ficha, sub-aba "Histórico de condição", botão "Mudar
  condição…", aba Desativados removida, cronograma mostra "Parecer da última"). 182 testes.
- **Sub-aba Calibrações: feita** (`interface/aba_calibracoes.py`: lista, registrar com
  resultado na hora e parecer final, ver pontos, Lixeira; `interface/grafico_tendencia.py`: um ponto
  por vez, erro ± U, tolerância, reprovado em vermelho, dica do mouse, salvar PNG). 192 testes.
- **Próximos passos:**
  1. ~~Aba Lixeira~~ feita (`interface/aba_lixeira.py`; 198 testes).
  2. ~~Trava de edição~~ feita (esquema **v4**, tabela `trava_edicao`; `regras/trava.py`;
     repositório `tentar_editar`/`dar_sinal`/`liberar_trava`, toda gravação recusada no modo
     consulta e "banco ocupado" vira aviso; janela com faixa amarela e "Passar para edição";
     identidade = usuário do Windows + nome do PC, em `app.py`).
     Depois, a pedido do usuário: sem faixa amarela nem botão — só o texto pequeno e branco no
     canto superior direito ("Modo edição" / "Modo consulta - usuário - PC"); passa sozinho para
     edição quando quem editava sai/para de responder; 30 min parado libera (se nada digitado
     sem salvar); **clicar no texto pede a edição** e quem edita recebe aviso Liberar / Continuar
     editando (vale para todos os projetos: ver CLAUDE.md do usuário). 218 testes.
     Peso medido (simulação de 20 anos, 2.000 calibrações): banco 2,4 MB, cronograma 14 ms.
  3. ~~Fechar a fase 4~~ feito: README, ADR 0002 (trava), versão `0.4.0`, PR #5.
- Fotos da tela: script em `dados/fotos/foto_janela.py` (fora do Git; rodar: `.venv/Scripts/python dados/fotos/foto_janela.py . dados/fotos/<pasta>`) (copia o banco para pasta temporária
  e cria calibrações de demonstração só na cópia); salvar em `dados/fotos/` e abrir eu mesmo com
  PowerShell `Invoke-Item`. Perguntas ao usuário: sempre com opções clicáveis (AskUserQuestion).

## Decisões em vigor (todas de 2026-10-29, combinadas com o usuário)
- **Importação:** conferência aprovada (123 instrumentos, 100 com plano, 987 pontos). Desativados
  antigos da planilha **não** entram (a planilha segue para consulta). Pontos sem U ficam sem U (fiel):
  148 numéricos (25 trenas, MIC-015, PAQ-013, ESC-006, 1 de ESC-005, 1 de LAF-017) e 21 limites — a U
  é preenchida na edição do plano (aviso amarelo) ou ao registrar.
- **Avaliação com U** (`regras/avaliacao.py`): numérico com nominal → `(medido − nominal) ± U` dentro da
  tolerância; **sem nominal fixo** (DUR-001 "67 a 80 HR15T"…, "Diferença entre 5 pontos" das balanças;
  laboratório externo) → o usuário digita o **erro** do certificado; **limite** → `medido + U ≤ máx` /
  `medido − U ≥ mín`; sem U → "não avaliado" (nunca U = 0; salvar bloqueado); **U negativa usada
  sem sinal**. **Classe** (EXT-001, MTR-001) e qualitativos: usuário escolhe Aprovado/Reprovado.
- **Resultado automático:** algum reprovado → Reprovado; senão Aprovado. **Todo ponto precisa ser
  preenchido** (em branco nunca é ignorado); "Não aplicável" exige motivo e não conta.
- **Parecer final e condição** (`regras/condicao.py`): parecer escolhido pelo usuário — **Aprovado** /
  **Orientação indicativa** / **Reprovado - Desativado** (reprovado não pode ser "Aprovado"). Condição
  do instrumento: **Em uso / Orientação indicativa / Desativado**, mudada pelo parecer ou manualmente
  (desativar/reativar), sempre com **data** e **observação/motivo opcional**, guardada em histórico.
  Orientação indicativa **segue no cronograma**; desativado sai. Lixeira = registro por engano.
  Calibração enviada à Lixeira **desfaz** a mudança de condição que o parecer dela fez
  (restaurar refaz). Lista de instrumentos abre em **"Todos menos desativados"**.
- **Visual "orientação indicativa":** onde aparecer, essas palavras em **letra vermelha `#c62828`
  sobre fundo amarelo `#ffd54f`** (etiqueta física da MG) — exceção consciente à regra de cores.
- **Corrigir calibração salva** (2026-10-30): pode corrigir **tudo menos a data** (data errada =
  Lixeira + registrar de novo); pontos reavaliados pela "foto" guardada; mudar o parecer ajusta a
  condição (recusado se a condição mudou depois da calibração); **cada correção é registrada sem
  pedir motivo**: quando, "usuário - PC" e cada mudança "antes → depois".
- **Cronograma de qualquer mês** (2026-10-30): seletor "Mês" na aba Cronograma ("Hoje — todos os
  instrumentos" + 12 meses para trás a 24 para frente = **limite da projeção**). No mês: Prevista,
  Situação (Feita / Pendente este mês / Vencida / Prevista), Feita em, Custo, Motivo do atraso.
  Meses futuros **projetam a periodicidade**. **Custo estimado do mês** = custo da calibração feita
  ou, se não feita, o **último custo registrado** do instrumento (sem custo = zero; não dizer de
  onde veio). **Atraso sem alarde**: "Feita" sempre verde, mesmo feita depois do mês.
- **Motivo do atraso** (2026-10-30): **opcional**. Vencida ainda não feita: botão "Informar motivo
  do atraso" no Cronograma (só aparece se houver vencida; some no modo consulta). Ao registrar
  calibração depois do mês previsto, aparece aviso discreto + campo do motivo, já preenchido com o
  informado; ele passa para a calibração (corrigível pelo Corrigir).
- **Textos da tela** (2026-10-30): botões **sem reticências**; título das janelas de calibração só
  com o **código** do instrumento (sem o tipo entre parênteses).
- **Visual "Reserva"** (2026-10-30): a palavra "Reserva" (ex.: "Laboratório - Reserva") em **fundo
  azul `#1565c0` com letra branca**, nos mesmos lugares da "orientação indicativa".
- **Localização padronizada** (`regras/localizacao.py`): "Laboratório", "Laboratório - Reserva",
  "Laboratório - Orientação indicativa"; qualquer "Orientativo/(indicativa)/(indic.)/Or. Ind." vira
  "<local> - Orientação indicativa". Aplicada ao importar e ao salvar.
- **Cronograma por mês** (`regras/cronograma.py`): Vencida (previsto para mês já terminado), Pendente
  este mês (até o último dia), Feita este mês, Próximo mês, Em dia, Sem calibração no programa (sem
  citar a DQ05), Sem periodicidade. Próxima = data + periodicidade (31/01 + 1 mês = 28/02).
- **Tela:** título "CALIBRAÇÃO DE INSTRUMENTOS"; topo **Instrumentos | Vencidas | CALIBRAÇÕES DE
  [MÊS] ("total | N pendentes") | CALIBRAÇÕES DE [MÊS SEGUINTE] (total)** — sem "Calibrações" nem
  "Sem calibração" no topo. Clicar em Vencidas/mês/mês seguinte abre **lista flutuante** (código,
  tipo, localização, data, situação) que fecha ao clicar fora. Escrever **"Incerteza (U)"** por extenso
  com tooltip.
- **Lixeira:** regras do protótipo (restaurar exige o pai ativo; excluir de vez digitando EXCLUIR, não
  com dependências), **exceto** que calibração pode ser excluída de vez (e leva os pontos medidos).
- **Banco/rede:** journal tradicional (nunca WAL), `busy_timeout`, backup diário em `backup/`
  (**30 cópias**), "foto" do ponto guardada em cada calibração.
- **Campos do protótipo a manter:** custo de compra e responsável (instrumento); custo e responsável
  (calibração). Modelo, nº de série, descrição e local da calibração: **não**.

### Histórico curto
- 2026-10-28: fase 0; importador (fase 1); banco novo em `dados/` + conferência.
- 2026-10-29: conferência aprovada; fases 1–3 juntadas; fase 4 iniciada; README de todos os
  repositórios do GitHub sem "como rodar" (PRs juntados em SistemaDeClassificacao, DataAnalytics,
  SmartCityDataPlatform).

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
