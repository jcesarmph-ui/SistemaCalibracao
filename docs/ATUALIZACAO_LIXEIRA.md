# Atualização: lixeira e sinalização de resultados

## Arquivos

- `main.py`: integra Lixeira ao menu, substitui a exclusão destrutiva, adiciona ações para planos, pontos e calibrações, sinaliza resultados e cronograma e mantém mensagens após recarregar a tela.
- `app/database/db.py`: backup SQLite consistente, verificação prévia, migração aditiva e índices.
- `app/services/lixeira_service.py`: exclusão lógica, busca paginada, contadores, consulta de detalhes, restauração e exclusão permanente protegida.
- `app/services/calibracao_service.py`: filtra registros excluídos e impede editar calibrações indisponíveis.
- `app/interface.py`: cores semânticas reutilizáveis, confirmação, restauração e interface da lixeira.
- `tests/test_lixeira.py`: testes em cópias temporárias do banco existente.
- `docs/auditoria_lixeira.json`: comparação dos dados anteriores e posteriores à migração aplicada neste projeto.

## Migração

Adiciona `excluido_em TEXT` e `motivo_exclusao TEXT` em equipamentos, calibrações, planos e pontos dos planos. Os novos campos começam nulos; `ativo` não é alterado. Cria índices por data de exclusão e por vínculo histórico ao ponto do plano. A migração é transacional e pode ser executada novamente.

Antes da primeira migração, a aplicação verifica integridade e chaves estrangeiras e salva uma cópia consistente em `data/backups/calibracao_antes_lixeira_<data_hora>.db`. Se a cópia falhar, a migração não prossegue. O banco continua em `data/calibracao.db`.

## Regras de uso

As ações **Enviar para a lixeira** aparecem na edição do equipamento, no cadastro/edição de planos e pontos e nos detalhes da calibração. Exigem confirmação e aceitam motivo opcional.

Excluir um pai não envia seus filhos individualmente à lixeira. Os vínculos e os snapshots históricos continuam armazenados. Um equipamento excluído oculta suas calibrações das operações; um plano excluído impede novas calibrações e oculta seus pontos operacionais. Os históricos já realizados permanecem consultáveis quando somente o plano ou o ponto está na lixeira.

Restaure primeiro o plano para restaurar seus pontos/equipamentos, e o equipamento para restaurar suas calibrações. Restauração não reativa um registro que já estava inativo. O plano indisponível continua vinculado ao equipamento; editar outros campos não troca esse vínculo automaticamente.

A exclusão permanente requer digitar **EXCLUIR** e nova validação no serviço. Calibrações nunca são apagadas permanentemente nesta versão. Equipamentos com calibrações, planos com equipamentos/pontos e pontos com históricos não podem ser apagados, mesmo que as dependências estejam na lixeira. Não há exclusão em cascata.

## Resultados, datas e incertezas

As células de resultado usam verde para aprovado, vermelho para reprovado, amarelo para pendência/restrição e cinza para estados sem avaliação. O resultado armazenado não é modificado pela cor. O cronograma usa cores consistentes para realizado, vencido, próximo e em dia; os meses continuam em português.

Os indicadores de vencimento usam a última calibração visível de cada equipamento. Ao excluir/restaurar uma calibração, a próxima data mostrada é derivada do histórico visível; as datas originais armazenadas no equipamento não são sobrescritas pela lixeira. As regras de periodicidade e aceitação com incerteza preenchida são mantidas.

Foram encontrados **64 pontos históricos numéricos** e **99 pontos numéricos de planos** sem incerteza preenchida. Não houve preenchimento nem substituição por zero. Na tela, esses resultados não são recalculados como se a incerteza fosse zero; salvar valores que dependam da incerteza ausente é bloqueado e pontos sem essa informação são omitidos do gráfico com aviso. Resultados históricos já gravados continuam preservados. A definição/preenchimento técnico dessas incertezas exige validação posterior.

## Testes

Execute na raiz do projeto:

```powershell
.venv\Scripts\python.exe -m unittest discover -s tests -v
```

Os testes copiam o banco para diretórios temporários em `tests`, nunca executam exclusões no original e conferem:

- preservação de todos os campos anteriores, inclusive incertezas, e migração idempotente;
- exclusão/restauração dos quatro tipos e vínculos originais;
- restauração bloqueada quando o pai está excluído;
- bloqueio de exclusões permanentes com histórico/dependências;
- confirmação, cancelamento e exclusão permanente permitida;
- filtros, pesquisa, mensagens e nova inicialização da aplicação;
- cores enviadas às células de resultado, cronograma e geração do gráfico;
- banco íntegro e sem violações de chaves estrangeiras.

## Validação manual e executável

Reinicie a aplicação para carregar o código atualizado. Confira o contraste e a legibilidade no monitor da empresa, o fluxo com registros representativos e as unidades/ausências de incerteza com o responsável técnico.

Nenhuma dependência nova foi adicionada. Não foi gerado um novo executável: o `.exe` já existente não deve ser considerado atualizado. Valide um novo pacote PyInstaller em uma cópia da instalação antes de substituir a distribuição; preserve o banco e seus backups. A localização do banco e o inicializador foram mantidos.

Não foram implementados login, usuários, autenticação ou concorrência. Os scripts antigos de correção/importação/limpeza são utilitários administrativos anteriores; não foram executados nesta atualização e não devem ser usados para o fluxo normal de exclusão, que agora é a Lixeira.
