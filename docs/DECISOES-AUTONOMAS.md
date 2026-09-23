# Decisões autônomas

Decisões fora dos ADRs, tomadas pelo agente executor. Formato: ticket, decisão, alternativa descartada, por quê.

| ticket | decisão | alternativa descartada | por quê |
|---|---|---|---|
| 04 | `JWT_SECRET` e `DEMO_PASSWORD` com default de dev em `app/config.py`. Produção sobrescreve no `.env`. | Exigir a chave no `.env` e falhar sem ela. | A chave não existe no `.env`. Default de dev destrava o ticket; o deploy (16) define o valor real. |
| 04 | Conta demo `demo@toneli.dev.br` criada no lifespan do FastAPI, idempotente. | Migração de dados no Alembic. | Reusa o hash de senha do FastAPI-Users sem duplicar lógica na migração. |
| 04 | `login_failed` via override de `UserManager.authenticate`. Payload só com o e-mail. | Middleware olhando status 400 da rota de login. | FastAPI-Users não tem hook de falha. O override fica no mesmo lugar dos outros eventos. |
| 04 | JWT com validade de 24 h, só Bearer. | Cookie + refresh token. | Aceite pede token em rota protegida. Refresh é YAGNI agora. |
| 05 | Conversa de outro Usuário responde 404. Filtro por `user_id` na própria query. | 403. | 404 não revela que a Conversa existe. Um caminho de código só. |
| 05 | Apagar Conversa é remoção física, CASCADE para Mensagens e Anexos. | Soft delete com `deleted_at`. | Aceite não pede recuperação. O Evento de auditoria guarda o `conversation_id`. |
| 05 | Mensagens ordenadas por `(created_at, id)`, `id` bigserial. | Só `created_at`. | `now()` é fixo na transação; o 06 grava usuário e assistente juntos. |
| 05 | `attachments` com `user_id` e `message_id` nulo. | `message_id` obrigatório. | O 09 faz upload antes da Mensagem existir. |
| 05 | Rotas em `/api/conversations`. | Sem prefixo `/api`. | Casa com `/api/chat` do 06 e separa da SPA do 07a. |
| 06 | Histórico vem só do banco. Do body do `useChat` o servidor usa só a última mensagem. | Confiar no histórico que o front manda. | Aceite pede histórico do banco. O front pode mandar histórico adulterado. |
| 06 | `messages.parts` guarda as partes do AI SDK (`dump_messages`/`load_messages` do `VercelAIAdapter`). | JSON nativo do Pydantic AI. | Casa com o `role` da tabela e com o front (07). Perde retry de tool e `provider_details` no round-trip, aceitável sem tools. |
| 06 | Usuário e assistente gravados juntos no `on_complete`. Turno com erro não grava nada. | Gravar a mensagem do usuário antes da chamada. | Sem mensagem órfã no histórico nem duplicada no retry. |
| 06 | Uso (`RunUsage`) só na última mensagem do assistente do turno. | Uso por `ModelResponse`. | Aceite fala de `RunUsage`. Com tools (10) o turno pode ter vários requests; o 08 decide se precisa quebrar. |
| 06 | 502 só quando o provedor falha antes do primeiro evento. Depois disso, erro vai como chunk do AI SDK. Os dois gravam `llm_error`. | Bufferizar a resposta inteira. | Depois do primeiro byte o status 200 já foi. Bufferizar mata o streaming. |
| 06 | Modelo injetado por dependência `modelo()`; testes trocam por `FunctionModel` ou `GoogleModel` com HTTP falso. | `agent.override`. | Override por request, sem estado global no Agent. |
| 07a | Componente `response` do AI Elements não existe mais no registry. Uso `MessageResponse` de `message`. | Instalar versão antiga do registry. | O registry atual fundiu `response` em `message`. Mesmo renderizador (streamdown). |
| 07a | Catch-all da SPA em `app/estaticos.py`, chamado na última linha de `main.py`. `/api/*` sem rota devolve 404, não HTML. Sem `web/dist`, não monta nada. | `StaticFiles(html=True)` montado em `/`. | `StaticFiles` não faz fallback de rota do front para `index.html`. Testes da API rodam sem build do front. |
| 07a | Tema dark padrão com toggle próprio (classe `dark` no `<html>` + `localStorage`). | `next-themes`. | Duas funções bastam. Uma dependência a menos. |
| 07a | Sem Evento de auditoria. | Emitir evento em acesso ao front. | Ticket não tem ação relevante do domínio: só serve arquivo estático e tela mock. |
| 07a | `loader` do AI Elements não existe no registry. Carregando usa `Spinner` + `Skeleton` do shadcn. | Escrever loader próprio. | Componentes prontos do shadcn, sem código novo. |
| 07a | Placeholders simulam estados por `?estado=carregando\|erro`; vazio é o padrão. Componentes em `web/src/components/estados.tsx`. | Estado só quando a API existir. | Guia exige estados visíveis; os tickets seguintes reusam os componentes. |
| 07a | Brave lançado pelo `executablePath` dentro do Playwright MCP (confirmado por `navigator.brave`). | Mudar a config do MCP. | Config do harness não é deste ticket. |
| 08 | Reserva estima o input localmente (~3 caracteres por token sobre as partes) + `max_output_tokens` inteiro. | `UsageLimits(count_tokens_before_request=True)`. | countTokens custa um request extra por turno, limita tokens e não dinheiro, e o `FunctionModel` dos testes não implementa. |
| 08 | Reserva não grava linha. O Ledger só recebe o acerto real, na mesma transação das Mensagens. | Linha de reserva + linha de estorno. | Aceite pede uma linha por chamada. Ressalva: duas chamadas simultâneas podem passar juntas do Cap. |
| 08 | Cap padrão em `config.py`: Usuário US$ 2, global US$ 20. Linha em `caps` sobrescreve (`user_id` nulo = global). | Semear o Cap na migração. | Menos dados fixos no banco; muda por `.env`. |
| 08 | Modelo sem linha na Tabela de Preço responde 500. | Debitar zero. | Crédito sem preço é número falso. O teste do 06 com `FunctionModel` passou a usar o nome do modelo real. |
| 08 | `max_tokens` = 8192 por request no chat. | Sem teto. | Sem teto a reserva não é teto real (research/02). |
| 08 | Ledger e Tabela de Preço sem UPDATE/DELETE para tess_app; Ledger sem FK para Conversa. | FK com CASCADE. | Saldo não pode mudar quando a Conversa é apagada. |
| 10 | Tool ativa na Conversa = `ativa_global` E toggle da Conversa. Sem linha em `conversation_tools`, herda `ativa_global` (seed: ligada). | Padrão desligado. | Demo usa busca sem clique extra. `ativa_global=false` vira chave geral. |
| 10 | `PUT /api/conversations/{id}/tools` recebe mapa parcial `{"web_search": false}`. Nome desconhecido = 422. Emite `tool_toggled`. | Lista de objetos ou rota por tool. | Um request liga várias; corpo mínimo para o switch do front. |
| 10 | Descrição que o modelo vê vem da coluna `tools.descricao`. A de `web_search` manda citar as URLs. | Docstring da função. | Registro único (ADR 0009); o aceite "cita a fonte" depende da instrução. |
| 10 | Erro da tool volta como texto para o modelo, não como exceção. | Levantar exceção. | O Agent roda com `retries=0`: exceção derruba o turno. |
| 10 | `tool_call` gravado por um `WrapperToolset` (`Auditada`), sessão própria, por execução. | Auditar dentro de cada função. | Um ponto só; o 17 (MCP) reusa. |
| 10 | Resultado cortado em 20.000 caracteres (fetch) e 600 por resultado (busca, 5 resultados). | Sem corte. | Página grande estoura contexto e Crédito. INFERIDO ~6k tokens. |
| 10 | HTTP das tools injetado por dependência `transporte()`; testes usam `httpx.MockTransport` com resposta gravada (Tavily real 1x, Jina real 1x). | Mockar as funções das tools. | Testa o parse e o fallback de verdade. Cliente separado por tool: header da Tavily não vaza para o Jina. |
