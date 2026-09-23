# Servidores MCP recomendados para a demo

Pesquisa de 2026-09-23. Fonte: doc oficial de cada fornecedor. O que não está na doc oficial está marcado **INFERIDO**.

## Critérios do nosso cliente (ADR 0009)

1. Servidor remoto em Streamable HTTP. Sem stdio. Sem SSE legado.
2. Auth por header `Authorization` fixo (Bearer, token, API key) ou sem auth. Servidor só com OAuth interativo não serve.
3. URL https.
4. Ação visível na demo: cria algo, devolve link, imagem ou dado real. Leitura de doc é secundária.

## Top 5 ranqueado

| # | Servidor | Endpoint | Transporte | Auth | Custo | Pergunta de demo (pt-BR) | O que aparece na tela |
|---|---|---|---|---|---|---|---|
| 1 | Stripe | `https://mcp.stripe.com` | Streamable HTTP (doc usa `--transport http`) | `Authorization: Bearer <agent API key>` | Sandbox grátis | "Cria um produto 'Consulta' de R$ 150 e me dá um link de pagamento." | Tool call `stripe_api_write`, depois um link `buy.stripe.com/test_...` clicável que abre o checkout real. |
| 2 | Linear | `https://mcp.linear.app/mcp` | Streamable HTTP (SSE em `/sse` é deprecated) | `Authorization: Bearer <Linear API key>` | Plano free (**INFERIDO**: limite de issues não conferido) | "Abre uma issue no Linear: 'Bug no upload de PDF', prioridade alta." | Tool call de criação e o link da issue. A issue aparece no Linear na hora. |
| 3 | Hugging Face | `https://huggingface.co/mcp` | Streamable HTTP stateless (modo JSON) | `Authorization: Bearer <HF token>`. Sem token cai no conjunto anônimo de tools. | Grátis | "Gera uma imagem 1024x1024 de um gato estilo Ghibli." ou "Quais os modelos mais baixados de OCR em português?" | Imagem gerada, ou lista de modelos com link e downloads. Nome da tool de imagem: **INFERIDO** (Space padrão tipo FLUX). |
| 4 | Zapier | `https://mcp.zapier.com/api/v1/connect` | Só Streamable HTTP. Doc diz: "does not support SSE". | `Authorization: Bearer <connection token>` (recomendado pela doc) | 2 tasks por chamada com sucesso. Plano free: **INFERIDO** (a doc não cita). | "Manda um e-mail pra mim com o resumo desta conversa." | Tool call da ação do Zapier. O e-mail chega de verdade na caixa. |
| 5 | DeepWiki | `https://mcp.deepwiki.com/mcp` | Streamable HTTP (SSE em `/sse` é legado) | Nenhuma | Grátis | "Como o repositório `pydantic/pydantic-ai` implementa o cliente MCP?" | Resposta fundamentada no repo com os tópicos da wiki. Só leitura. |

### Por que essa ordem

- **Stripe** é o melhor efeito de demo. Uma frase vira um link de pagamento real. Mostra também o risco: a tool escreve em sistema de terceiro. Usar só a chave de sandbox. A partir de 2026-10-31 a Stripe só aceita Agent Key ou OAuth. Criar a chave já como Agent Key.
- **Linear** mostra o mesmo padrão "cria algo e devolve link" com setup de dois minutos. Bom plano B do Stripe.
- **Hugging Face** mostra saída não textual. Só vale se o chat renderizar imagem vinda de tool MCP. Conferir antes da entrevista.
- **Zapier** mostra efeito fora da tela (e-mail chega). Custa tasks do plano. Configurar a ação antes, porque o servidor começa vazio sem apps conectados.
- **DeepWiki** não pede conta nem chave. Funciona sempre. É a rede de segurança se todo o resto falhar ao vivo.

### Outros aprovados (não entram no top 5)

| Servidor | Endpoint | Auth | Motivo de ficar fora do top 5 |
|---|---|---|---|
| GitHub | `https://api.githubcopilot.com/mcp/` | `Authorization: Bearer <PAT>` | Já é o servidor da demo no ADR 0009. Cria issue e PR. Mantido como padrão, não precisa de pesquisa. |
| Supabase | `https://mcp.supabase.com/mcp` | `Authorization: Bearer <personal access token>` | Executa SQL e cria tabela. Efeito forte, mas pode destruir dados ao vivo. Usar só com projeto descartável. |
| Context7 | `https://mcp.context7.com/mcp` | `Authorization: Bearer <API key>`, chave grátis | Só leitura de doc de biblioteca. Transporte não está explícito na doc (**INFERIDO** Streamable HTTP pelo path `/mcp`). |
| Exa | `https://mcp.exa.ai/mcp` | Sem auth (keyless com rate limit). Com chave usa header `x-api-key`, não `Authorization`. | Busca web. Duplica nossa tool nativa `web_search`. |
| Tavily | `https://mcp.tavily.com/mcp/` | `Authorization: Bearer <API key>` ou query param | Duplica nossa `web_search`, que já usa Tavily. Serve para comparar nativa x MCP na mesma chave. |
| Firecrawl | `https://mcp.firecrawl.dev/v2/mcp` | Keyless (limite diário) ou Bearer com API key | Scraping. Duplica nossa `web_fetch`. Transporte: **INFERIDO** Streamable HTTP. |
| Apify | `https://mcp.apify.com` | `Authorization: Bearer <APIFY_TOKEN>` | Roda Actors de scraping. Crédito grátis: **INFERIDO** (a doc de MCP não cita). |
| Smithery (Connect) | `https://mcp.smithery.run/{namespace}` | `Authorization: Bearer <SMITHERY_API_KEY>` | Agregador. Um endpoint expõe vários servidores. Servidor upstream com OAuth exige setup prévio no painel. Camada extra na demo. |
| Cloudflare Docs | `https://docs.mcp.cloudflare.com/mcp` | Nenhuma | Só leitura de doc. Os outros servidores Cloudflare (Radar, Browser Run) aceitam API token em Bearer segundo a página geral. Detalhe por servidor: **INFERIDO**. |

## Descartados

| Servidor | Motivo |
|---|---|
| Notion | Doc oficial só cita OAuth para o servidor hospedado. Integration token só funciona no servidor self-hosted stdio, que a Notion não mantém mais. |
| Sentry | Doc oficial: "All connections use OAuth." |
| Vercel | OAuth, e só aceita clientes revisados e aprovados pela Vercel. Nosso cliente não está na lista. |
| Brave Search | Não tem endpoint remoto oficial. O servidor oficial roda em stdio ou HTTP local. Endpoint remoto só via terceiro (Apify). |
| Pipedream | Exige access token de OAuth client-credentials, que expira (**INFERIDO**: validade não conferida), mais cinco headers `x-pd-*` por usuário. Não é header fixo. |
| Composio | Auth por header `x-api-key`, não `Authorization`. Só entra se o cliente aceitar header arbitrário. |

## Para a entrevista

1. "O cliente só fala Streamable HTTP porque stdio num app multiusuário é executar processo arbitrário no nosso servidor, e SSE legado foi deprecado pela própria spec e pelos fornecedores (DeepWiki, Linear e Zapier já marcam ou recusam SSE)."
2. "Auth é um header fixo porque o Servidor MCP é cadastrado por URL e usado sem ninguém na frente do navegador, então um fluxo OAuth interativo por usuário não cabe no escopo do desafio."
3. "A consequência é que servidores só-OAuth como Notion e Sentry ficam de fora, e isso é uma escolha consciente: OAuth com Dynamic Client Registration é o próximo passo, não um esquecimento."
