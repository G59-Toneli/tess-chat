# Estudo: Jev, MCP e tool calling

Revisão de Jev, MCP e tool calling (29/09/2026): como o Jev força a tool e como o conector MCP funciona. Todo `arquivo:linha` foi conferido no código de 29/09. Caminhos `pydantic_ai/...` ficam em `api/.venv/Lib/site-packages/`.

## 1. Tool calling: o loop do agente

**Ideia central:** o modelo não executa nada. Ele escreve texto. Parte desse texto sai num formato combinado (`functionCall`) que quer dizer "chame a função X com estes argumentos". O código executa e chama o modelo de novo com o resultado.

**Analogia:** um consultor trancado numa sala, sem mãos e sem memória. A cada bilhete você manda o dossiê inteiro (o histórico) e a lista de serviços que sabe fazer (as declarações de função). Ele devolve a resposta final ou um pedido de serviço. Você faz o serviço e manda o dossiê de novo, com o resultado grampeado.

**Direção da rede:** o backend sempre liga para o Google (POST HTTPS em `.../models/<modelo>:streamGenerateContent?alt=sse`, `google/genai/models.py:4756`). O Google só responde, em stream SSE. O `functionCall` é o conteúdo da resposta, não uma chamada de volta. Caminho: `app/chat.py:83` (GoogleModel) → `pydantic_ai/models/google.py:907-914` (monta o JSON e chama o SDK) → SDK `google-genai` → HTTPS.

**O que trafega:**
```json
// request 1
{"contents":[{"role":"user","parts":[{"text":"qual a cotação do dólar hoje?"}]}],
 "tools":[{"functionDeclarations":[{"name":"web_search","parameters":{"type":"object",
   "properties":{"query":{"type":"string"}},"required":["query"]}}]}],
 "toolConfig":{"functionCallingConfig":{"mode":"ANY","allowedFunctionNames":["web_search"]}}}
// response 1
{"parts":[{"functionCall":{"name":"web_search","args":{"query":"cotação dólar hoje"}}}]}
// request 2: histórico + o functionCall + {"functionResponse":{"name":"web_search","response":{...}}}
// response 2: {"parts":[{"text":"O dólar está em R$ 5,40 ..."}]}  → fim
```

**Como o código sabe qual função chamar:** busca num dicionário pelo nome. O nome enviado na declaração e a chave do dicionário são a mesma string, e o Google só devolve um dos nomes que recebeu.
- Registro: `ts.add_function(..., name=tool.nome)` (`app/tools.py:329`). O schema sai da assinatura Python `buscar(query: str)` (`app/tools.py:443`) ou do `inputSchema` do servidor MCP.
- Declaração: `_function_declaration_from_tool` (`pydantic_ai/models/google.py:2028`).
- Leitura da resposta: `part.function_call.name` e `.args` (`pydantic_ai/models/google.py:1567-1572`).
- Busca: `tool = self.tools.get(name)` (`pydantic_ai/tool_manager.py:550`). Nome desconhecido vira `ModelRetry` com a lista dos nomes válidos (`:562`).
- Dono de cada nome: `CombinedToolset` (`pydantic_ai/toolsets/combined.py:18-24`); nome repetido entre toolsets dá `UserError` (`:10`).

**Pseudocódigo fiel:**
```python
while True:
    resposta = gemini.post(historico, declaracoes, tool_config)   # um POST novo por passo
    pedidos = [p for p in resposta.parts if p.function_call]
    if not pedidos:
        break                                   # só texto: fim do turno
    for p in pedidos:                           # pode vir mais de um por passo
        tool = tools.get(p.name)                # nome desconhecido → erro volta ao modelo
        args = tool.validar(p.args)             # schema errado → erro volta ao modelo
        historico.append(function_response(p.name, tool.executar(**args)))
```

**Consequências:**
- 3 tools em sequência = 4 requests. Cada request reenvia tudo o que veio antes, incluindo os resultados das tools anteriores. O custo cresce mais rápido que o número de passos.
- Erro de tool (schema ou execução) vira `ModelRetry`: volta ao modelo, que pode corrigir. `retries=1` no Agent (`app/chat.py:77`).
- Quem decide parar é o modelo, respondendo só texto. Isso quer dizer que ele decidiu responder, não que a resposta está certa.
- O código só para o loop por fora: `ComTeto` (teto de chamadas `tool_limit_reached`, servidor MCP caído, falha seguida `tool_falhou`), botão Parar (`CancellationToken`, ADR 0023) e erro do provedor sem fallback.
- Gemini 3: o primeiro `function_call` de um turno leva `thoughtSignature`, que precisa voltar no histórico (`pydantic_ai/models/google.py:1754`).
- Validação de schema garante formato, não conteúdo: `query: ""` passa nas duas validações.

## 2. Jev: como ele força a tool

**Analogia:** triagem de pronto-socorro. A enfermeira (Jev) não trata; ela manda direto pro raio-X quando está segura. Na dúvida, quem decide é o médico (Gemini).

**Passo a passo:**
1. `_rotear` (`app/chat.py:146`, chamado em `:461`) junta o texto da última mensagem, os nomes dos anexos e as tools ativas.
2. Opções = tools ativas + `nenhuma`, com descrição (`app/roteador.py:58-60`; descrições das nativas em `:27-31`).
3. `client.system_one(state=..., questions={"tool": Choice(...)})` (`app/roteador.py:65`). O Jev devolve escolha, confiança e distribuição.
4. `apply_gate` (`app/roteador.py:85-88`) força só se: escolha ≠ `nenhuma`, confiança ≥ limiar (0.7, configurável) e origem ≠ `mcp`.
5. O Gate devolve `tool_choice=["web_search"]` só no passo 1 (`app/roteador.py:97-99`, `ctx.run_step == 1`).
6. O adaptador do Google traduz para `function_calling_config: {mode: ANY, allowed_function_names: [...]}` (`pydantic_ai/models/google.py:819-852`). `AUTO` = modelo decide; `ANY` = obrigado a chamar uma função da lista; `NONE` = proibido.
7. Falha do Jev (sem chave, timeout de 5 s, erro) → AUTO + evento `router_fallback` (`app/chat.py:163-175`). Sem retry (`app/roteador.py:47`).
8. Custo no Ledger e evento `router_decision` com a distribuição (`app/chat.py:178-199`).

**Exemplo real** (auditoria local, 24/09 01:16):
```
router_decision {"tool":"web_search","confidence":1.0,"forcada":true,"limiar":0.7,"distribution":{"web_search":1.0,...}}
tool_call       {"tool":"web_search","origem":"nativa","args":{"query":"notícias de hoje"},"result_chars":1931}
```

**Por que as regras são assim:**
- **Só no passo 1**, por dois motivos. O Jev só vê a mensagem do usuário, que não muda no turno, então repetiria a mesma escolha. E `ANY` proíbe resposta em texto: valendo em todo passo, o modelo nunca terminaria.
- **Não força `nenhuma`:** o AUTO já responde direto; forçar só perde a busca se o Jev errar.
- **Não força MCP** (ADR 0005, emenda 23/09): nomes e descrições de servidor externo são genéricos, e o Jev não vê o histórico. No Stripe, "gera o pagamento" forçou o `implementation_planner` e o turno acabou sem ação. A decisão fica registrada com `sugerida=true`.
- **Passar histórico e schema ao Jev** transformaria o Jev num segundo Gemini, com latência em todo turno e porta de injeção pelo resultado das tools.

**O que NÃO está provado:** o golden set mediu o acerto do Jev (9 de 9, `api/tests/fixtures/jev_golden.json`). Ninguém mediu o Gemini sozinho nos mesmos casos. No spike, o Gemini chamou a busca sozinho para "cotação do dólar hoje" (`spike/RESULTADO.md:226`). O ganho do Jev é hipótese. Para provar: golden set com e sem o Jev.

## 3. MCP: como o conector funciona

**O que é:** protocolo padrão para expor ferramentas a modelos. JSON-RPC 2.0 sobre Streamable HTTP. Transforma N × M integrações em N + M.

**Papéis:** host (backend do tess-chat), client (um `MCPToolset` por servidor), server (Stripe, Notion). O servidor pode publicar tools, resources e prompts; o tess-chat usa só tools.

**JSON-RPC:** request (tem `id`), response (mesmo `id`, `result` ou `error`), notification (sem `id`, não espera resposta).

**Streamable HTTP:** uma URL; cada mensagem é um POST; a resposta vem em JSON ou SSE; o header `Mcp-Session-Id` amarra a sessão. O stdio (processo filho conversando por stdin e stdout) caiu porque, num SaaS, significaria rodar no servidor um comando escolhido pelo usuário: execução de código remoto, com acesso ao disco e ao `.env`.

**Conversa real com o `mcp-demo`** (`curl` local, porta 8765, 29/09):
```
→ {"id":1,"method":"initialize","params":{"protocolVersion":"2025-06-18",...}}
← {"id":1,"result":{"capabilities":{"tools":{...}},"serverInfo":{"name":"tess-mcp-demo"}}}  + Mcp-Session-Id
→ {"method":"notifications/initialized"}                          ← HTTP 202
→ {"id":2,"method":"tools/list"}
← {"tools":[{"name":"somar","inputSchema":{"properties":{"a":{"type":"number"},"b":{"type":"number"}},"required":["a","b"]}},...]}
→ {"id":3,"method":"tools/call","params":{"name":"somar","arguments":{"a":2,"b":40}}}
← {"content":[{"type":"text","text":"42.0"}],"isError":false}
sem Mcp-Session-Id ← {"error":{"code":-32600,"message":"Missing session ID"}}  HTTP 400
```

**Os 5 momentos no tess-chat:**
1. **Cadastro** (`cadastrar`, `app/mcp.py:204`): `validar_url` contra SSRF (só https, IP público, `app/mcp.py:73`); `initialize` + `tools/list`; nada grava se falhar. Cada tool vira `<slug>_<4hex>_<tool>` (`app/mcp.py:53-58`, `:180-199`). Não chama tool para testar (quem testa com request real é a Tool por API, ADR 0024). Token cifrado com Fernet.
2. **Autenticação:** header fixo (Bearer) ou OAuth com DCR (ADR 0022, `app/mcp_oauth.py`): descobrir o servidor de login pelo 401 (`_descobrir`, `:88`), registrar o app sozinho (`_registrar`, `:119`), login com PKCE, renovar antes do turno se estiver para vencer (`renovar`, `:171`, chamado em `app/tools.py:338`).
3. **Sonda antes do turno** (`alcancavel`, `app/mcp.py:88`): `initialize` + `tools/list` com teto de 3 s. Falhou: servidor sai do turno, evento `mcp_server_unreachable`, turno segue.
4. **Toolset do turno** (`app/mcp.py:99-102`): `MCPToolset(url, headers).prefixed(prefixo).filtered(ativas)`, dentro do `CombinedToolset` e embrulhado em `Auditada` e `ComTeto` (`app/tools.py:317-361`, `app/chat.py:471`).
5. **Uma chamada, camada por camada:**
   `tools.get(nome)` → `ComTeto` (conta; `app/tools.py:421`) → `Auditada` (desembrulha, valida, grava `tool_call`; `app/tools.py:271`) → `CombinedToolset` (acha o dono; `combined.py:95`) → `PrefixedToolset` (tira o prefixo; `prefixed.py:38`) → `MCPToolset` (`tools/call` com Bearer e `Mcp-Session-Id`) → resultado volta como `function_response`.

**Por que o Gemini não fala direto com o servidor MCP:** o token do usuário nunca sai do backend; toda chamada passa por auditoria, crédito e teto; o backend pode cortar, bloquear ou pedir confirmação antes de executar; o toolset não depende do Gemini (o fallback do ADR 0012 usa o mesmo). Custo: um salto pelo backend, não medido.

**Erros:**
- Servidor cai antes do turno: sonda tira, turno segue.
- Servidor cai no meio do turno: `ComTeto` corta o turno, grava o parcial e cobra (`app/tools.py:430-433`).
- `isError: true` (servidor vivo, tool falhou): o `MCPToolset` transforma em `ModelRetry` (`pydantic_ai/mcp.py:1458-1467`, `:1762`, padrão `'retry'`). Volta ao modelo; segunda falha seguida corta com `tool_falhou` (`app/tools.py:434-435`).

**Remendos que vieram de bug real:**
- `schema_para_modelo` (`app/tools.py:224`, ticket 35): objeto sem propriedades vira string com JSON dentro, só na declaração enviada ao Gemini.
- `desembrulhar_json` (`app/tools.py:197`, ticket 33): converte de volta antes do `tools/call`.
- Erro de tool volta ao modelo como texto (ticket 31).
- A `Auditada` troca o validador de cada tool por um que aceita tudo e valida por conta própria (`app/tools.py:263-283`): até chamada inválida passa pela auditoria.

## 4. Limitações conhecidas (resposta para "o que está ruim no teu sistema?")

| Limitação | Onde | Próximo passo |
|---|---|---|
| DNS rebinding no MCP: a URL só é validada no cadastro; sonda e turno resolvem o DNS de novo sem validar | `app/mcp.py:70`, `:208` | validar o IP na hora da conexão (ticket 86) |
| Jev travado custa até 5 s por turno | `app/roteador.py:32` | circuit breaker |
| Ganho do Jev não medido | `jev_golden.json` | golden set com e sem o Jev |
| Cap não checado entre passos; a reserva não segura saldo | ADR 0023, `docs/LACUNAS.md` | reserva gravada no Ledger |
| Turno com MCP abre duas conexões por servidor (sonda e sessão) | `app/tools.py:343`, `app/mcp.py:99` | reaproveitar a sessão da sonda |
| Nenhuma métrica de qualidade das respostas | — | Jev como juiz em segundo plano, validado contra um golden set rotulado à mão |

## 5. Vocabulário técnico
- `isError` é do protocolo MCP; `ModelRetry` é do Pydantic AI.
- Teto de chamadas (`tool_limit_reached`) ≠ falha seguida (`tool_falhou`).
- SSRF (*Server-Side Request Forgery*); DNS rebinding.
- Notificação JSON-RPC: mensagem sem `id`.
- `AUTO`, `ANY`, `NONE`, `VALIDATED`: modos de `function_calling_config` do Gemini.

## 6. Boas práticas ao responder sobre o sistema

1. Confirmar no código antes de afirmar (revalidação de DNS, "o Gemini respondeu de memória", "não corta o turno"). Na dúvida: "acho que X, preciso confirmar".
2. Número só vale com o ambiente declarado. Não usar um número de um contexto em outro (ex.: os ~50 ms do relay da voz não valem para o MCP).
3. Usar cada conceito no lugar certo: `isError` é do MCP, não de tool nativa; teto de chamadas é diferente de falha seguida.

Perguntas para refazer: as camadas do `tools/call`; os três jeitos de o turno ser cortado; "como saber que o Jev ajuda?".
