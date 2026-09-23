# 40 — Imagem de turno anterior volta ao modelo

**Type:** bug (só api/)
**Status:** resolved
**Blocked by:** nenhum
**Refs:** ADR 0016. Produção, conversa `2d7bd6bf` em 23/09: o Gemini inventou raça e texto de uma imagem no turno seguinte ao anexo.

**Problema:** `sem_bytes` trocava toda imagem do histórico por `[anexo: nome]`. O modelo perdia a imagem sem saber.

**Aceite:**
- [x] Teste: imagem do turno 1 vai como `inlineData` no request do turno 2.
- [x] Teste: imagem sumida do disco vira o aviso `fora do contexto`, sem `inlineData`.
- [x] Teste: PDF de turno anterior continua como texto, agora com o aviso.
- [x] Sem chamada real a Gemini, Tavily ou Jev.

## Answer
- `anexos.partes_do_historico` substitui `sem_bytes`. Imagem própria volta com bytes; outro arquivo vira `FORA_DO_CONTEXTO`.
- Mensagens que vão para o Resumo não levam imagem.
- `_estimar_input` soma `TOKENS_IMAGEM` = 1120 por imagem.
- REVISAR(human): comentário acima de `partes_do_historico`.
