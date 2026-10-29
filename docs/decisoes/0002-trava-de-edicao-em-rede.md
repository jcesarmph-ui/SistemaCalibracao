# 0002 — Trava de edição para uso em pasta de rede

- **Data:** 2026-10-29
- **Situação:** aceita

## Contexto
O programa fica numa pasta comum da rede, sem servidor, com o banco SQLite ao lado do `.exe`.
Quase sempre uma pessoa usa por vez, mas às vezes duas ou três abrem ao mesmo tempo. O SQLite
garante que gravações não se misturem (uma por vez), mas cada tela mostra o que leu ao abrir:

- duas pessoas editando a mesma ficha ou o mesmo plano → quem salva por último apaga, sem perceber,
  o que a outra mudou;
- duas pessoas registrando calibração no mesmo instrumento → calibração duplicada;
- quem só olha fica com números desatualizados.

O usuário pediu algo como o "somente leitura" do Excel, mas **sem** deixar a pessoa mudar coisas que
depois não consegue salvar.

## Decisão
1. **Uma pessoa edita por vez.** Uma tabela `trava_edicao` (uma linha) guarda quem edita: usuário do
   Windows, nome do computador, desde quando e um "sinal" que sobe a cada 30 segundos. Pegar a trava
   é uma transação `BEGIN IMMEDIATE` (duas pessoas não pegam ao mesmo tempo).
2. **Quem abre depois entra em modo consulta:** botões de mudar escondidos, campos sem digitação,
   dados relidos a cada 30 s. Indicação discreta no canto superior direito ("Modo edição" ou
   "Modo consulta - usuário - PC").
3. **A trava vence** quando o sinal fica parado 2 minutos (contados pelo relógio de quem observa,
   para não depender de relógios iguais) ou tem mais de 10 minutos; e quem edita libera ao ficar
   30 minutos parado, se não houver nada digitado sem salvar. Quem consulta passa sozinho para
   edição quando a trava fica livre.
4. **Pedido de edição:** clicar no texto do modo consulta avisa quem edita, que escolhe liberar ou
   continuar.
5. **Proteção no repositório:** toda gravação é recusada no modo consulta, e "banco ocupado" vira
   aviso na tela.
6. Identificação **sem senha** (usuário do Windows + PC): a senha não resolve o problema de duas
   pessoas ao mesmo tempo, e o uso é interno.

## Consequências
- Os problemas de "último que salva ganha" e de calibração duplicada deixam de existir.
- Quem abre enquanto outro edita espera ou pede a liberação; com uma pessoa usando, nada muda.
- Se o computador de quem edita ficar parado com algo digitado, a edição só é liberada quando a
  pessoa voltar ou fechar o programa.
- Vira padrão para os próximos programas da empresa.
