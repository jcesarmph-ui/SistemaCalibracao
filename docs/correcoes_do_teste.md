# Correções pedidas no teste (2026-11-03)

Lista do usuário depois de usar o programa de TESTE. Cada item = uma correção, mostrada por foto
e aprovada antes de seguir. Marcar `[x]` quando aprovado.

## Regra geral (vale para tudo)
- **Tudo precisa ser mais indicativo**: deixar claro o que é **só apresentação**, o que **permite
  editar** e o que é para **inserir dados**, para ninguém editar sem querer nem ficar sem saber
  para que um dado aparece.
- **Tela cheia demais → abrir aba ou janela nova**, em vez de apertar os espaços.

## Itens

### Tela em geral
- [x] 1. (proteção feita: rolagem dentro da janela; a rolagem some com os itens 10/12) A parte de baixo do programa fica **coberta pela barra do Windows** (escondia "Registrar
      calibração", "Gráfico de tendência" e "Restaurar").
- [x] 2. (botões, abas, filtros, caixinhas, células, painéis do topo e o texto do canto clareiam; desligado não muda) **Passar o mouse sobre o que é clicável**: aumentar o brilho ou mudar a opacidade (não
      só contorno, para não poluir). O que não é clicável não muda.
- [x] 3. ("✔ Salvo" verde na linha das abas, 3,5 s, em toda gravação; a tela passou a se atualizar em 0,16 s em vez de 3,3 s) **Aviso de "Salvo" / "Mudança feita"** toda vez que salvar ou aplicar uma mudança.
- [x] 4. (no programa inteiro; pacote de teste ainda NÃO gerado com isto) **Scroll horizontal com Shift + roda do mouse** onde ele for necessário.
- [x] 5. **Caixinhas (Reserva, Orientação indicativa, Precisa de calibração) invisíveis** no fundo
      preto: precisam de contorno branco.

### Trava de edição (dois PCs)
- [x] 6. (botões "Pedir edição" e "Atualizar" pequenos, ao lado do texto do canto; só no modo consulta) **Botão para pedir a edição** no canto, junto do "Modo consulta - usuário - PC".
- [x] 7. (aviso verde "Edição liberada" / vermelho "Pedido recusado" por 6 s + contorno do texto do canto: amarelo esperando, verde aceito, vermelho recusado) Quem pediu recebe um **sinal verde (aceito) ou vermelho (recusado)**: contorno ou aviso na cor.
- [x] 8. (consulta relê a cada 10 s; botão "Atualizar" só quando outro PC edita) Como aparecem as mudanças que o outro PC fez: hoje atualiza sozinho a cada ~30 s.
      Decidir com o usuário se quer também um botão "Atualizar".

### Aba Instrumentos
- [x] 9. (código em azul sublinhado com mãozinha e dica; linha aberta em cinza com linhas brancas) Na lista, deixar claro que o **código é um botão** que abre os dados, e **destacar o
      instrumento aberto** (contorno ou cor), para não ter que comparar a lista com a ficha.
- [x] 10. **Ficha só de apresentação**; para editar, botão **EDITAR** que abre a ficha numa janela no
      meio da tela (como o aviso de pedido de edição), deixando claro que ali se edita.
- [x] 11. (a ficha virou texto; a janela de edição é larga) Campos da ficha **estreitos demais**: o texto aparece cortado (só a metade de cima).

### Plano de calibração
- [x] 12. (resumo na aba + janelas VER PLANO e EDITAR PLANO; um clique já edita; coluna "U não se aplica") Não deu para editar o plano ("clicar duas vezes" não ficou claro) e o painel é **estreito,
      com scroll horizontal**. Quero:
      - botão **VER PLANO** → janela grande, só apresentação, com o plano completo;
      - botão chamativo de **editar plano** → janela grande onde se edita, deixando claro que é edição.

### Calibrar (o mais importante)
- [x] 13. (feito em 2026-11-03, aguardando aprovação por foto) **Não achei onde fazer uma calibração.** Quero uma **aba nova "CALIBRAR"** (além de
      Instrumentos, Cronograma e Lixeira), com a lista de instrumentos igual à primeira e, ao lado,
      o botão chamativo **NOVA CALIBRAÇÃO**:
      - abre a janela com os pontos e os campos para digitar os desvios etc.;
      - **SALVAR CALIBRAÇÃO** → ela aparece na lista de calibrações feitas do instrumento, com
        todos os dados;
      - clicar numa calibração feita → mostra o plano com os valores, **só apresentação**; para
        mexer, botão **EDITAR**.
- [x] 14. (fica na aba Calibrar, embaixo das calibrações) **Botão do gráfico de tendência** não foi encontrado (provavelmente estava escondido
      pela barra do Windows — conferir depois do item 1).

### Lixeira
- [x] 15. (estava sob a barra do Windows e some no modo consulta, de propósito; agora fica logo abaixo da lista, com dica) **Sem o botão RESTAURAR** (provavelmente escondido pela barra do Windows — conferir
      depois do item 1).

### Dados
- [x] 16. **Incertezas (U) faltando** nos planos — corrigido em 2026-11-03:
      - 90 pontos (18 trenas) ganharam a U: a planilha tinha 0,2, mas sem a data da calibração;
      - "-" ou "N/A" onde vai a U = **incerteza não se aplica** (avaliado só pelo valor): Planeza e
        Paralelismo de MIC-001/005/010, ESC-005, LAF-017;
      - **na trena**, "-" ou "N/A" = passou a ser **orientação indicativa**: TRE-167, 182, 200 e 201
        ganharam a marca; os numéricos ficam com a última U em número;
      - trena com orientação indicativa é calibrada **só nos pontos qualitativos**;
      - continuam sem U, fiel à planilha (nada escrito): ESC-006, MA-09/11/12, MIC-007/009/011/
        013/014 (Planeza e Paralelismo), MIC-015, PAQ-013, TRE-113.
      Banco da entrega remontado da DQ05 (cópia do anterior em `dados/`).

### Gráfico de tendência
- [ ] 17. (pedido de 2026-11-03, ainda não feito) **Gráfico com todos os pontos juntos**, um de
      cada cor, como **opção principal**: é o primeiro a aparecer ao abrir; os gráficos de um ponto
      por vez continuam na mesma lista, para quem quiser ver um por um.
      - Tolerâncias iguais em todos os pontos → eixo em **erro** (mesma unidade), com as linhas de
        tolerância comuns; tolerâncias diferentes → eixo em **% da tolerância usada** (limite
        ±100%). O programa escolhe sozinho e diz no título qual está usando.
      - Pontos qualitativos ficam de fora (não têm número).
      - **Não pode ficar bagunçado** nem um ponto cobrindo o outro: é para entender de relance
        (ex.: afastar um pouco para o lado os pontos da mesma data, U mais fina, legenda clara).

### Decisões já tomadas
- Ordem: 1 → 13/14 → 15 → 9/10/11 → 12 → 2 a 5 → 6 a 8 (16 logo depois do 1).
- Item 8: atualizar sozinho a cada **10 s** + botão **"Atualizar"** no modo consulta.
