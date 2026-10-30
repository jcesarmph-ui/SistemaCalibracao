# 0003 — Lugar oficial do banco (cópia só consulta)

- **Data:** 2026-10-30
- **Situação:** aceita

## Contexto
A trava de edição (ADR 0002) mora **dentro** do arquivo do banco, então só coordena quem abre o
**mesmo arquivo**. Se alguém copiar a pasta do programa para outro lugar (a própria área de
trabalho, por exemplo) e abrir a cópia, ela tem a sua própria trava: a pessoa fica em "Modo edição"
e grava calibrações que ninguém mais vê e que não voltam para o banco oficial. E, se só o `.exe`
for copiado para uma pasta `dados` sem banco, o SQLite criaria um banco vazio sem avisar.

## Decisão
1. O banco guarda o **caminho do lugar oficial** (`metadados.pasta_oficial`). Banco sem essa marca
   (o da entrega) adota o primeiro lugar de onde for aberto.
2. Aberto de outro lugar, o programa fica **só em consulta**, com aviso amarelo mostrando onde está o
   oficial. A trava da cópia não é usada.
3. Se a pasta oficial mudou de verdade (todos fecharam e a pasta foi movida), basta clicar no aviso
   e digitar **MUDAR** — o mesmo tipo de confirmação do "EXCLUIR" da Lixeira.
4. A mesma pasta da rede pode ter caminhos diferentes em cada PC (letra de unidade ou
   `\\servidor\...`). Quando o oficial está acessível, pergunta-se ao Windows se é o **mesmo
   arquivo**; só quando não está é que se compara o texto do caminho.
5. **Nunca criar banco vazio:** sem `dados/calibracao.db`, o programa mostra erro.

## Consequências
- Cópia esquecida ou aberta por engano não gera dados perdidos; serve só para consulta.
- Mudar o programa de pasta exige um passo consciente (digitar MUDAR) uma única vez.
- Na entrega, o banco precisa ir **sem** a marca de lugar oficial (se tiver sido aberto em outro
  lugar durante a preparação, apagar a marca antes).
