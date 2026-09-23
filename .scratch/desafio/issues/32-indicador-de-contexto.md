# 32 — Indicador da janela de contexto na barra do input

**Type:** task (AFK)
**Status:** ready-for-agent
**Blocked by:** nenhum
**Refs:** ADR 0006 (compactação), ticket 14 (Configuração), `docs/UI-GUIA.md`, `api/app/conversas.py`, `web/src/pages/Chat.tsx`. Pedido do Toneli em 23/09: "igual ao claude.ai".

**What to build:**
1. **Back.** `GET /api/conversations/{cid}/contexto` devolve `{usado, limite, limiar_compactacao, modelo}`. `usado` = `input_tokens` da última Mensagem do assistente da Conversa (é o que o próximo turno vai carregar, mais a pergunta nova); 0 em conversa nova. `limite` = janela de contexto do modelo em uso, resolvida pela Configuração (conversa → usuário → `.env`): tabela em `config.py` por modelo (`gemini-3.8-flash`, `gemini-3.7-flash`, flash-lite); valores da doc do Google, marcados INFERIDO se não confirmados. `limiar_compactacao` = o resolvido pela Configuração. Sem migração.
2. **Front.** Componente `IndicadorContexto` na barra do input, à direita do botão "N tools": rosca SVG de 18 a 20 px, arco proporcional a `usado/limite`, cor `muted-foreground` até 70 %, âmbar de 70 a 90 %, vermelho acima. Segunda marca fina no arco na posição do `limiar_compactacao`. Hover (Tooltip do shadcn): "Contexto: 12,4 mil de 1 mi tokens (1,2 %) · restante 987,6 mil · compacta em 100 mil · gemini-3.8-flash". Atualiza ao fim de cada turno e ao trocar de conversa. Em conversa nova mostra a rosca vazia com "Contexto vazio".
3. Depois de uma compactação, o indicador cai: isso é o efeito visível do ADR 0006 na demo.

**Aceite:**
- [ ] Teste do endpoint: conversa com 2 turnos devolve `usado` igual ao `input_tokens` da última resposta; conversa nova devolve 0; `limite` muda ao trocar o modelo na Configuração da Conversa.
- [ ] Screenshot dark `32-indicador-contexto.png` com o tooltip aberto, e `32-indicador-contexto-alto.png` com uso simulado acima de 70 % (pode ser via limite baixo num modelo de teste).
- [ ] `tsc`, `npm run build`, `uv run pytest tests/test_conversas.py` (ou onde couber) verdes.
