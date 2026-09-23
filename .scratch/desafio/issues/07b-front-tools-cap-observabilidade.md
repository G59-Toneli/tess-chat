# 07b — Front: tool calls visíveis, cap, painel de tools, roteador

**Type:** task (AFK)
**Status:** blocked
**Blocked by:** 07, 10, 11
**Refs:** ADR 0004, 0005, 0009. `docs/UI-GUIA.md`.

**What to build:** no chat (`web/src/pages/Chat.tsx` e componentes): renderizar partes de tool call do stream como bloco recolhível (nome, args, duração, resultado resumido) usando `tool` do AI Elements; indicador "buscando na web…" enquanto a tool roda; badge discreto no fim da resposta com o modelo usado e tokens (dados do `usage` final). Erro 402 (cap) vira mensagem própria em pt-BR com link para `/creditos`, não toast genérico. Painel lateral da conversa com as tools e switches (GET/PUT `/api/conversations/{id}/tools`). Tela `/tools` integrada (GET `/api/tools`, toggle global). Se o roteador (11) expõe a decisão no stream ou em endpoint, mostrar "roteado para web_search (0.91)" como linha discreta acima do bloco de tool.

**Aceite:**
- [ ] Pergunta que dispara `web_search` mostra bloco de tool com fontes e a resposta cita fonte.
- [ ] Com cap em 1 micro-USD, a UI mostra a mensagem de cap e o botão para créditos.
- [ ] Desligar `web_search` no painel e repetir a pergunta: sem bloco de tool.
- [ ] Screenshots dark: tool-call, cap, painel-tools, tela-tools.
