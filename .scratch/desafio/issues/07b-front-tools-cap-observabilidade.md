# 07b — Front: tool calls visíveis, cap, painel de tools, roteador

**Type:** task (AFK)
**Status:** resolved
**Blocked by:** 07, 10, 11
**Refs:** ADR 0004, 0005, 0009. `docs/UI-GUIA.md`.

**What to build:** no chat (`web/src/pages/Chat.tsx` e componentes): renderizar partes de tool call do stream como bloco recolhível (nome, args, duração, resultado resumido) usando `tool` do AI Elements; indicador "buscando na web…" enquanto a tool roda; badge discreto no fim da resposta com o modelo usado e tokens (dados do `usage` final). Erro 402 (cap) vira mensagem própria em pt-BR com link para `/creditos`, não toast genérico. Painel lateral da conversa com as tools e switches (GET/PUT `/api/conversations/{id}/tools`). Tela `/tools` integrada (GET `/api/tools`, toggle global). Se o roteador (11) expõe a decisão no stream ou em endpoint, mostrar "roteado para web_search (0.91)" como linha discreta acima do bloco de tool.

**Aceite:**
- [x] Pergunta que dispara `web_search` mostra bloco de tool com fontes e a resposta cita fonte.
- [x] Com cap em 1 micro-USD, a UI mostra a mensagem de cap e o botão para créditos.
- [x] Desligar `web_search` no painel e repetir a pergunta: sem bloco de tool.
- [x] Screenshots dark: tool-call, cap, painel-tools, tela-tools.

## Answer
Chat: bloco recolhível por tool call (nome, args, duração, resultado resumido, fontes do `web_search`), "Buscando na web…" enquanto roda, badge de modelo e tokens, linha "roteado para X (conf.)" quando o Roteador forçou a Tool, 402 como aviso próprio com botão para `/creditos`. Painel lateral de tools por Conversa e tela `/tools` com toggle global e schema. API: `PUT /api/tools/{nome}` (evento `tool_toggled_global`, migração 0008) e `GET /api/conversations/{id}/roteador`.
Verificado no Brave: turno real com 2 `web_search` e resposta citando a PEP 745; cap de 1 µUSD mostra o aviso sem toast; com `web_search` desligada o turno não chamou `web_search`.
Ressalva: no turno com `web_search` desligada o Gemini chamou `web_fetch` numa URL do histórico, então aparece um bloco de `web_fetch`. O toggle global está liberado a qualquer Usuário.
Screenshots: `.scratch/desafio/screens/07b-*.png`.
