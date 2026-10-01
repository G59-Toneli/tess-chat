# 41 — Imagem de turno anterior volta ao modelo
> Commits `feat(40): imagem-no-historico` e `feat(40): pdf-no-historico` são deste ticket. O número 40 colidiu com `40-descricao-drive-no-banco`.

**Type:** bug (só api/)
**Status:** resolved
**Blocked by:** nenhum
**Refs:** ADR 0016. Produção, conversa `2d7bd6bf` em 23/09: o Gemini inventou raça e texto de uma imagem no turno seguinte ao anexo.

**Problema:** `sem_bytes` trocava toda imagem do histórico por `[anexo: nome]`. O modelo perdia a imagem sem saber.

**Aceite:**
- [x] Teste: imagem do turno 1 vai como `inlineData` no request do turno 2.
- [x] Teste: imagem sumida do disco vira o aviso `fora do contexto`, sem `inlineData`.
- [x] Teste: PDF do turno 1 vai como `inlineData` no turno 2, com `media_resolution` medium.
- [x] Sem chamada real a Gemini, Tavily ou Jev.

## Answer
- `anexos.partes_do_historico` substitui `sem_bytes`. Anexo próprio (imagem e PDF) volta com bytes; outro arquivo vira `FORA_DO_CONTEXTO`.
- Mensagens que vão para o Resumo não levam imagem.
- `_estimar_input` soma `TOKENS_IMAGEM` = 1120 por imagem.
