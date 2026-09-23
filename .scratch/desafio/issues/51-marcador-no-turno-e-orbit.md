# 51 — Separador antes do turno que compactou e indicador Orbit na Compactação

**Type:** task (api/ e web/)
**Status:** resolved
**Refs:** ticket 49. Pedido do Toneli em 23/09, depois de testar o 49 em produção.

**Problema:** o separador ficava depois da última Mensagem coberta pelo Resumo. Isso é certo nos dados, mas na tela parece que a compactação aconteceu vários turnos antes de quando aconteceu de fato. E o "Compactando histórico…" usava o mesmo indicador do "Pensando…", só com o texto trocado.

**Decisão (Toneli, 23/09):** o separador vai antes da pergunta do turno que compactou, com o texto "Histórico anterior resumido". O indicador passa a ser a variante Orbit do Loading State do beautifului.dev (MIT): células quadradas, centro apagado, cometa rodando pela borda. O site não tem componente de compactação. Alternativa descartada: anel girando que vira badge com check (visual novo no chat, e com ~1 s quase não aparece).

## Answer
Back: `GET /api/chat/{id}/compactacao` devolve também `turno_message_id`, a 1ª Mensagem `user` criada depois do Resumo vigente. Funciona porque o Resumo é gravado durante o turno, antes das Mensagens dele. Testes do endpoint atualizados.
Front: `MarcadorCompactacao` põe o separador antes da Mensagem. Numa compactação durante a sessão, o separador vai para a pergunta do próprio turno (penúltima da lista do useChat). Com isso saiu a tradução de id por posição (`idNoChat`) do ticket 49. `Trabalhando` ganhou `orbita`, e o tempo recomeça do zero ao trocar de indicador.
Validado no browser local (API com o código novo em :8010, Flash-Lite), com 1 chamada ao chat e 1 ao Resumo: ao carregar a página, o separador apareceu antes da 4ª pergunta. Depois apareceram "Pensando…" e "Compactando histórico…" com o Orbit. No fim do turno, o separador foi para antes da pergunta nova, sem reload. Screenshots: `screens/51-marcador-antes-do-turno.png`, `screens/51-compactando-orbit.png`.
