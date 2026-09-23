# 02 — Modelos: Gemini, Cohere, TypeSafe Jev, compactação e custo

Pesquisa feita em 2026-09-22 contra fontes primárias. Cada afirmação tem URL. O que não foi confirmado em fonte primária está marcado **INFERIDO**.

## Achados principais

1. **O Google agora recomenda a Interactions API para projeto novo.** A Interactions API está GA desde junho de 2026 e a doc diz que ela substitui o `generateContent` legado em projetos novos. Fonte: https://ai.google.dev/gemini-api/docs/interactions-overview
2. **O Gemini não tem compactação nativa de histórico para chat comum.** A compactação automática (~135k tokens) existe só no agente Antigravity. No chat, a compactação é código nosso. Fonte: https://ai.google.dev/gemini-api/docs/antigravity-agent
3. **O Jev é só texto, tem limite de 32k no state e é treinado principalmente em inglês.** Nosso app é em português. Precisa de smoke test antes de usar. Fonte: https://docs.typesafe.ai/models.md
4. **O free tier do Gemini usa o conteúdo para melhorar produtos.** Os PDFs dos avaliadores iriam para esse uso. O paid tier não usa. Fonte: https://ai.google.dev/gemini-api/docs/pricing

---

## 1. Gemini API

### 1.1 Duas formas de API (não misturar)

| Aspecto | `generateContent` (clássica) | Interactions API (GA jun/2026) |
|---|---|---|
| Status | Chamada de "legado" para projeto novo | "Generally Available and recommended for all new projects" |
| Estado da conversa | Cliente reenvia o histórico inteiro | Opcional no servidor via `previous_interaction_id` |
| Retenção | n/a | 55 dias no paid, 1 dia no free; `store=false` desliga |
| Nomes de usage | `promptTokenCount`, `candidatesTokenCount`, `thoughtsTokenCount`, `cachedContentTokenCount`, `toolUsePromptTokenCount`, `totalTokenCount` | `total_input_tokens`, `total_output_tokens`, `total_thought_tokens`, `total_cached_tokens`, `total_tool_use_tokens`, `total_tokens` |
| Forçar tool | `function_calling_config.mode` = `AUTO`/`ANY`/`NONE`/`VALIDATED` + `allowedFunctionNames` | `tool_choice` = `auto`/`any`/`none`/`validated` + `allowed_tools` |

Fontes:
- Interactions: https://ai.google.dev/gemini-api/docs/interactions-overview
- Usage da `generateContent`: https://ai.google.dev/api/generate-content
- Usage da Interactions: https://ai.google.dev/gemini-api/docs/tokens
- `FunctionCallingConfig`: https://ai.google.dev/api/caching
- `tool_choice`: https://ai.google.dev/gemini-api/docs/function-calling

### 1.2 Modelos atuais (texto)

Fonte da lista: https://ai.google.dev/gemini-api/docs/models

| ID | Status | Contexto in / out | Observação |
|---|---|---|---|
| `gemini-3.8-flash` | Stable, set/2026 | 1.048.576 / 65.536 | "our most intelligent Flash model". Entrada texto, imagem, vídeo, áudio, PDF. Thinking low/medium/high. |
| `gemini-3.7-flash`, `gemini-3.6-flash` | Stable | INFERIDO (igual ao 3.8) | Geração anterior |
| `gemini-3.5-flash` | Stable, legado | INFERIDO | Mais caro que o 3.8 |
| `gemini-3.5-flash-lite` | Stable | INFERIDO | Mais rápido e barato da linha 3.5 |
| `gemini-3.1-flash-lite` | Stable | INFERIDO | O mais barato disponível para projeto novo |
| `gemini-3.1-pro-preview` | Preview, fev/2026 | 1.048.576 / 65.536 | Não tem free tier. Variante `gemini-3.1-pro-preview-customtools` para agente com tools custom. |
| `gemini-2.5-*` | Acesso restrito | — | "restricted to prior users". Projeto novo não usa. |

Fontes das specs:
- 3.8 Flash: https://ai.google.dev/gemini-api/docs/models/gemini-3.8-flash
- 3.1 Pro: https://ai.google.dev/gemini-api/docs/models/gemini-3.1-pro-preview

Embedding: `gemini-embedding-2-preview` é multimodal (texto, imagem, vídeo, áudio, PDF). `gemini-embedding-001` é só texto. Fonte: https://ai.google.dev/gemini-api/docs/models

### 1.3 Preço paid tier (USD por 1M tokens)

Fonte: https://ai.google.dev/gemini-api/docs/pricing

| Modelo | Input | Output (inclui thinking) | Cache | Free tier |
|---|---|---|---|---|
| `gemini-3.8-flash` | 0,75 | 3,75 | 0,075 | Sim |
| `gemini-3.7-flash` / `3.6-flash` | 0,75 | 3,75 | 0,075 | Sim |
| `gemini-3.5-flash` | 1,50 | 9,00 | 0,15 | Sim |
| `gemini-3.5-flash-lite` | 0,30 | 2,50 | 0,03 | Sim |
| `gemini-3.1-flash-lite` | 0,25 | 1,50 | 0,025 | Sim |
| `gemini-3.1-pro-preview` (≤200k) | 2,00 | 12,00 | 0,20 | Não |
| `gemini-3.1-pro-preview` (>200k) | 4,00 | 18,00 | 0,40 | Não |

- O preço do 3.8/3.7/3.6 Flash dobra em 2027-01-01. Isso não afeta a semana da demo.
- A doc diz que o output inclui os thinking tokens.
- Batch e Flex custam 50% menos. Priority custa 80% a mais.
- Grounding com Google Search: 5.000 requests grátis por mês, depois US$ 14 por 1.000.
- Free tier: "Used to improve our products: Yes". Paid tier: "No".

### 1.4 Rate limits do free tier

- A doc oficial não publica os números. Ela manda ver o painel do AI Studio: https://aistudio.google.com/rate-limit. Fonte: https://ai.google.dev/gemini-api/docs/rate-limits
- Paid tier tem limite por gasto: Tier 1 = US$ 10 por 10 min; Tier 2 = US$ 50; Tier 3 = US$ 200. Fonte: https://ai.google.dev/gemini-api/docs/rate-limits
- **INFERIDO:** sites de terceiros divergem para o 3.8 Flash no free tier (de ~20 RPD até 1.500 RPD). Não confiar. Conferir no painel no dia 1.

### 1.5 PDF e imagem

Fontes:
- PDF: https://ai.google.dev/gemini-api/docs/document-processing
- Métodos de entrada: https://ai.google.dev/gemini-api/docs/file-input-methods
- Resolução: https://ai.google.dev/gemini-api/docs/media-resolution
- Tokens: https://ai.google.dev/gemini-api/docs/tokens

Limites:
- PDF: até 50 MB ou 1.000 páginas.
- Inline: até 100 MB por request. Para PDF, 50 MB.
- Files API: até 2 GB por arquivo e 20 GB por projeto. O arquivo expira em 48 h.
- URL externa: até 100 MB por payload.
- A página de PDF é reduzida para até 3072x3072 e ampliada para no mínimo 768x768.
- A visão de documento só entende PDF de verdade. TXT, HTML e Markdown viram texto puro.

Custo em tokens no Gemini 3 (`media_resolution`):

| Mídia | low | medium | high | ultra_high | Default |
|---|---|---|---|---|---|
| Imagem | 280 | 560 | 1120 | 2240 | 1120 |
| Página de PDF | 280 + texto nativo | 560 + texto nativo | 1120 + texto nativo | — | 560 |

- A doc recomenda `medium` para PDF: "quality typically saturates at `medium`".
- O texto nativo extraído do PDF não é cobrado.
- **Conflito na doc:** a página de PDF diz 258 tokens por página. A página de `media_resolution` diz 560 no default do Gemini 3. Considerar 560 para estimar custo. Medir com `count_tokens` no dia 1.

### 1.6 Function calling

Fonte: https://ai.google.dev/gemini-api/docs/function-calling

- Suporta chamada paralela: várias funções no mesmo turno.
- Suporta chamada composicional: funções em sequência.
- Modos: `AUTO` (default), `ANY` (sempre chama função), `NONE`, `VALIDATED` (valida a chamada com constrained decoding). Fonte: https://ai.google.dev/api/caching
- `allowedFunctionNames` limita as funções quando o modo é `ANY` ou `VALIDATED`. Com uma função só na lista, a chamada fica forçada.
- O Gemini 3 usa thought signatures. Os SDKs cuidam delas sozinhos.
- O SDK Python tem automatic function calling. Desliga com `AutomaticFunctionCallingConfig(disable=True)`. Fonte: https://github.com/googleapis/python-genai

### 1.7 Contagem de tokens e streaming

- `usage_metadata` volta em toda resposta. Os campos estão na tabela 1.1. Fonte: https://ai.google.dev/api/generate-content
- `count_tokens` conta texto, system instruction, imagem, vídeo, áudio e definição de tools. Fonte: https://ai.google.dev/gemini-api/docs/tokens
- O SDK Python também tem tokenizer local: `local_tokenizer.LocalTokenizer()`. Fonte: https://github.com/googleapis/python-genai
- **INFERIDO:** a doc não diz se `count_tokens` é grátis nem se consome RPM.
- **INFERIDO:** a doc não diz se `usage_metadata` vem em todo chunk do streaming ou só no último. Testar no dia 1.
- **INFERIDO:** a doc não diz se `thoughtsTokenCount` está dentro de `candidatesTokenCount` ou separado. Testar no dia 1 antes de somar os dois.
- Streaming: `generate_content_stream()` no Python e `generateContentStream()` no JS. Fontes: https://github.com/googleapis/python-genai e https://github.com/googleapis/js-genai

### 1.8 Context caching

Fonte: https://ai.google.dev/gemini-api/docs/caching

- Cache implícito vem ligado por default no 2.5 e em todos os modelos mais novos.
- Mínimo para cache implícito: 4.096 tokens nos modelos 3.x. 2.048 no 2.5.
- Para ter hit: conteúdo grande e fixo no começo do prompt. Requests com o mesmo prefixo em pouco tempo.
- O token de cache custa ~10% do input (tabela 1.3).

### 1.9 MCP

- Os dois SDKs têm MCP nativo **experimental**. Texto do README: "Built-in MCP support is an experimental feature. You can pass a local MCP server as a tool directly."
  - Python: passa a `ClientSession` do MCP direto em `tools` do `GenerateContentConfig`. Fonte: https://github.com/googleapis/python-genai
  - JS/TS: converte o client MCP com `mcpToTool()`. Fonte: https://github.com/googleapis/js-genai
- A Interactions API diz: "Gemini 3 does not support remote MCP, this is coming soon." Fonte: https://ai.google.dev/gemini-api/docs/interactions-overview
- **INFERIDO:** o suporte cobre só tools (`list_tools`), sem resources e prompts. Fonte secundária: https://medium.com/google-cloud/model-context-protocol-mcp-with-google-gemini-llm-a-deep-dive-full-code-ea16e3fac9a3

---

## 2. Cohere

Fonte de modelos: https://docs.cohere.com/docs/models

| Tipo | IDs | Nota |
|---|---|---|
| Chat | `command-a-plus-05-2026` (128k), `command-a-03-2025` (256k), `command-a-vision-07-2025` (128k), `command-a-reasoning-08-2025` (256k), `command-r7b-12-2024` | — |
| Embed | `embed-v4.0` | Texto, imagem e misto (PDF). Dimensões 256/512/1024/1536. |
| Embed | `embed-multilingual-v3.0` (1024), `-light-v3.0` (384) | Texto e imagem |
| Rerank | `rerank-v4.0-pro`, `rerank-v4.0-fast` (32k) | — |
| Rerank | `rerank-v3.5`, `rerank-multilingual-v3.0` (4k) | — |

Limites do trial key. Fonte: https://docs.cohere.com/docs/rate-limits
- Chat: 20 req/min.
- Embed: 2.000 inputs/min. Embed de imagem: 5 inputs/min.
- Rerank: 10 req/min.
- **1.000 chamadas por mês no total.** Esse é o limite que trava.

Preço: **INFERIDO.** A página https://cohere.com/pricing não mostrou os valores por token na extração. A doc explica só o modelo de cobrança. Fonte: https://docs.cohere.com/docs/how-does-cohere-pricing-work

Serve para RAG? Sim para rerank (`rerank-v4.0-fast`) e embed (`embed-v4.0`). O limite de 1.000 chamadas/mês cabe numa demo pequena, mas cada upload de PDF gasta chamadas de embed. **INFERIDO:** `gemini-embedding-2-preview` evita uma segunda chave e um segundo limite.

---

## 3. TypeSafe AI e o Jev

Índice da doc: https://docs.typesafe.ai/llms.txt

### O que é

- Jev é o primeiro modelo "System One" da TypeSafe. Ele não gera texto. Ele responde perguntas tipadas sobre um `state` e devolve probabilidade. Fonte: https://docs.typesafe.ai/introduction
- Três tipos de pergunta (fonte: https://docs.typesafe.ai/primitives.md):
  - **Noul:** sim/não, devolve probabilidade de 0 a 1.
  - **Choice:** escolhe uma opção de uma lista (até 255 opções), com distribuição e `confidence`.
  - **Score:** nota numa rubrica de 2 a 10 níveis, com `confidence`.
- Várias perguntas vão no mesmo request e rodam em paralelo.
- Lançado em "early access" em set/2026. Fonte: https://typesafe.ai/blog/introducing-system-one-models-and-jev

### API

Fonte: https://docs.typesafe.ai/api.md

- `POST https://api.typesafe.ai/v1/systemone` com `Authorization: Bearer <API_KEY>`.
- Body: `state` (string, objeto ou array), `model` (`jev-latest`), `questions` (mapa nome → pergunta).
- Resposta: `answers` com as mesmas chaves, e `usage` com `input_tokens` e `output_tokens`.
- Erros: 401, 422, 429 e 529. A doc manda retry com backoff exponencial.

Exemplo de request (da doc):

```json
{
  "state": "Help! My payouts have been failing for 3 days.",
  "model": "jev-latest",
  "questions": {
    "is_urgent": {
      "type": "noul",
      "instructions": "Does this convey urgency?",
      "criteria": {"true": "Explicitly time-sensitive", "false": "No urgency"}
    }
  }
}
```

### SDKs

- Python: `typesafe-sdk`, import `typesafe_sdk`, clients `TypeSafeClient` e `AsyncTypeSafeClient`. Env var `TYPESAFE_API_KEY`. Fonte: https://docs.typesafe.ai/sdk/python.md
- JS/TS: `@typesafe-ai/sdk`, Node 20+, ESM e CJS, infere o tipo da resposta a partir das perguntas. Fonte: https://docs.typesafe.ai/sdk/javascript.md

### Modelo, limites e preço

Fonte: https://docs.typesafe.ai/models.md

- Versão atual: `jev-1.13.0`. `jev-latest` e `jev-preview` apontam para ela hoje.
- Preço: US$ 0,042 por 1M tokens de input. Output é grátis.
- Rate limit: 250.000 tokens/s e 1.200 req/min, "can change without notice".
- Contexto: 64k no total. 32k para `state` + a maior pergunta.
- **Só texto.** Sem imagem, áudio ou vídeo.
- **"English as the primary training language."**
- Latência: 70 ms a 500 ms. Fonte: https://typesafe.ai/blog/introducing-system-one-models-and-jev

### Pontos fracos declarados (jev-1.13)

Fonte: https://docs.typesafe.ai/model-jaggedness/jev-1.13.md

- Lê a pergunta ao pé da letra. Negação e condição implícita confundem.
- Não conta nem calcula.
- Compara data mal.
- Perde precisão com `state` grande e cheio de conteúdo não relacionado.
- Não trata conteúdo adversarial como hostil. Prompt injection no `state` pode mudar a resposta.
- Nouls complementares não somam 1 de forma garantida.
- A página não fala de português.

### Onde encaixa no nosso chat

- Roteamento de intenção com gate de confiança: https://docs.typesafe.ai/patterns/intent-routing.md e https://docs.typesafe.ai/patterns/confidence-routing.md
- Guardrail de entrada e saída: https://docs.typesafe.ai/cookbooks/llm_guardrails.md
- Filtro de trechos de RAG antes do modelo principal: https://docs.typesafe.ai/cookbooks/classifying_rag_passages.md
- Escolher tool/skill: https://docs.typesafe.ai/cookbooks/skill_suggestion.md e https://docs.typesafe.ai/cookbooks/function_calling.md

A informação é escassa fora da doc oficial. O modelo saiu há uma semana.

---

## 4. Compactação automática de histórico

| Sistema | Como faz | Gatilho | Fonte |
|---|---|---|---|
| Claude Code | Resume o histórico antigo. `/compact <instruções>` diz o que preservar. Seção "Compact instructions" no CLAUDE.md. | Janela configurável (`/autocompact`, `CLAUDE_CODE_AUTO_COMPACT_WINDOW`). Default: perto do limite do modelo, ~967k nos modelos de 1M. | https://code.claude.com/docs/en/model-config, https://code.claude.com/docs/en/costs |
| Anthropic API, compaction | O servidor troca os turnos antigos por um resumo. Dois modos: on demand e por threshold. Dá para manter os últimos turnos literais. | Threshold de input tokens que o cliente define | https://platform.claude.com/docs/en/build-with-claude/compaction |
| Anthropic API, context editing | Apaga resultados antigos de tool (`clear_tool_uses_20250919`) e thinking antigo (`clear_thinking_20251015`). Não resume. | Default 100k input tokens, mantém 3 tool uses. Tem `clear_at_least` para compensar a perda do cache. | https://platform.claude.com/docs/en/build-with-claude/context-editing |
| OpenAI Responses | `context_management` com `compact_threshold` no servidor, ou endpoint `/responses/compact`. Devolve um item de compactação criptografado e opaco. | `compact_threshold` | https://developers.openai.com/api/docs/guides/compaction |
| LangChain/LangGraph | `SummarizationMiddleware`: resume o antigo e mantém os `keep` mais recentes (default 20 mensagens). `ClearToolUsesEdit`: troca resultado velho de tool por `[cleared]`. | `trigger` por tokens, mensagens ou fração do limite. `ClearToolUsesEdit` default 100k. | https://docs.langchain.com/oss/python/langchain/middleware/built-in |
| Gemini | Sem compactação nativa no chat. Só o agente Antigravity compacta (~135k). A Interactions API guarda estado, mas não compacta. | — | https://ai.google.dev/gemini-api/docs/antigravity-agent |

Padrão comum entre todos:
1. Gatilho por contagem de tokens, bem abaixo do limite da janela.
2. Os últimos N turnos ficam literais.
3. O resto vira um resumo, com instrução do que preservar.
4. Par chamada de tool + resultado nunca é separado. **INFERIDO:** a doc do LangChain citada não detalha essa regra. É prática padrão para não quebrar a validação de tool call.
5. O resumo invalida o cache do prefixo. Por isso ninguém compacta a cada turno.

---

## 5. Estimativa de custo da demo (1 semana)

Premissas:
- 500 mensagens do usuário.
- Input médio por chamada: 10k tokens (system + tools + histórico com anexos, já compactado).
- Output médio: 1.500 tokens (resposta + thinking).
- 20 anexos: 10 PDFs de 10 páginas a 560 tokens/página, e 10 imagens a 1.120 tokens. Isso dá ~67k tokens na primeira ida. O peso real vem do anexo repetido no histórico, já contado no input médio.
- Sem desconto de cache. Com cache implícito, o custo real cai.
- Câmbio: **INFERIDO** R$ 5,50 por US$.

Totais: 5M tokens de input e 0,75M de output.

| Modelo | Input | Output | Total USD | Total R$ (INFERIDO) |
|---|---|---|---|---|
| `gemini-3.8-flash` | 3,75 | 2,81 | **6,56** | ~36 |
| `gemini-3.1-pro-preview` | 10,00 | 9,00 | **19,00** | ~105 |
| `gemini-3.5-flash-lite` | 1,50 | 1,88 | **3,38** | ~19 |
| `gemini-3.1-flash-lite` | 1,25 | 1,13 | **2,38** | ~13 |
| Jev (500 roteamentos × 2k tokens) | 0,04 | 0 | **0,04** | ~0,23 |

Cenário pessimista: input médio de 30k tokens (sem compactação boa).
- `gemini-3.8-flash`: ~US$ 14.
- `gemini-3.1-pro-preview`: ~US$ 39. Com o thinking do Pro dobrando o output, ~US$ 48.

O dinheiro não é o gargalo. O gargalo é o RPD do free tier e o fato de o Pro não ter free tier.

---

## Recomendação

- **Chat principal: `gemini-3.8-flash` no paid tier.** É stable, tem 1M de contexto, faz tool calling paralelo, PDF, imagem e thinking. O paid tier custa pouco e tira os PDFs dos avaliadores do uso para treino. O Pro não compensa o custo ~3x numa demo.
- **Visão e PDF: o mesmo `gemini-3.8-flash`.** Usar `media_resolution` `medium` para PDF. PDF até 50 MB vai inline. PDF reutilizado vai pela Files API e expira em 48 h.
- **API: decidir entre `generateContent` e Interactions no dia 1.** A Interactions é a recomendada. A `generateContent` tem mais exemplo pronto e deixa o histórico no nosso banco, o que a compactação própria exige de qualquer jeito. Recomendo `generateContent` pela previsibilidade em 2 dias. **INFERIDO:** a `generateContent` continua suportada no curto prazo.
- **Classificação e roteamento barato: Jev, com condição.** Antes de ligar, rodar ~10 requests com trechos reais em português (Noul + Choice). Se errar, cair para `gemini-3.1-flash-lite` com structured output. Usar `confidence` como gate: abaixo do limiar, vai para o modelo principal.
- **RAG, se tiver:** `gemini-embedding-2-preview` para embed. `rerank-v4.0-fast` da Cohere só se o rerank provar ganho, porque o trial tem 1.000 chamadas/mês.
- **MCP (bônus):** usar o MCP experimental do SDK com servidor local. Remoto não funciona no Gemini 3.
- **Compactação:** fazer no nosso código.
  1. Gatilho: `promptTokenCount` passa de um limiar de custo (ex.: 100k), não do limite de 1M.
  2. Manter os últimos N turnos literais. Nunca separar tool call do resultado.
  3. Resumir o resto com o Flash-Lite e guardar o resumo no banco.
  4. Manter o system prompt fixo no começo para o cache implícito (mínimo 4.096 tokens) continuar batendo.
- **Teto de crédito:**
  1. Antes da chamada: estimar o input com `count_tokens` ou o tokenizer local. Somar a reserva de `max_output_tokens`. Recusar se passar do saldo.
  2. Depois da chamada: debitar o valor real do `usage_metadata`. Input normal a preço de input, `cachedContentTokenCount` a preço de cache, output + thinking a preço de output.
  3. Travar `max_output_tokens` e o nível de thinking por request, para a reserva ser um teto real.
  4. **INFERIDO, testar no dia 1:** se o `usage_metadata` vem só no último chunk do streaming, e se `thoughtsTokenCount` já está dentro de `candidatesTokenCount`. Sem isso, o débito pode contar thinking duas vezes ou nenhuma.
  5. No Jev, debitar `usage.input_tokens` × US$ 0,042/1M.
