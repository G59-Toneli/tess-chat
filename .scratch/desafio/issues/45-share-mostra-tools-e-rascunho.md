# 45 — Link público mostra cards de tool e o rascunho de e-mail (só leitura)

**Type:** task (AFK, web/ e, se preciso, api/app/shares.py)
**Status:** ready-for-agent
**Blocked by:** nenhum
**Refs:** ADR 0008 (compartilhamento), ADR 0013 (envio com confirmação), `docs/UI-GUIA.md`, ticket 37 (indicador). Feedback do Toneli em 23/09 com print de `/s/<id>`.

**Problema:** `web/src/pages/Compartilhamento.tsx` desenha só as partes de texto (`textoDe`) e esconde mensagens sem texto. Os cards de tool (`BlocoTool`) e o card do rascunho de e-mail (`RascunhoEmail`) somem. Quem abre o link lê "o rascunho está na sua tela" e não vê rascunho nenhum.

**What to build:**
- A página pública desenha as partes da mensagem do assistente como o Chat desenha: texto, cards de tool (`BlocoTool` e helpers de `components/BlocoTool.tsx`), marcador de compactação se houver, e o `RascunhoEmail`. Reusar os componentes do Chat, não duplicar.
- `RascunhoEmail` ganha modo só leitura (ex.: prop `somenteLeitura`): mostra para, assunto, corpo e o estado (pendente/enviado/descartado), sem botões Enviar/Descartar/editar e sem chamar a API autenticada. No link público é sempre só leitura.
- Nada da página pública chama endpoint autenticado. Se o estado do Rascunho só vem de endpoint autenticado, mostrar o que está na saída da tool gravada na mensagem; se precisar do estado real, expor no `SharePublico` sem dado além do que a mensagem já mostra.
- Anexos da conversa (imagem/PDF) no link: fora do escopo; manter como hoje.

**Aceite:**
- [ ] Screenshot dark 1440x900 `45-share-rascunho.png` de um link com card de tool e card de rascunho visíveis, sem botão Enviar.
- [ ] Teste (ou checagem no Brave com API mockada) de que a página pública não faz nenhuma requisição a `/api/` fora de `/api/s/{id}`.
- [ ] Chat logado continua com o rascunho clicável (sem regressão).
- [ ] `tsc` e `npm run build` limpos.
