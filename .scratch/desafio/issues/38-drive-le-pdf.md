# 38 — `drive_search_read` lê PDF do Drive

**Type:** task (AFK, só api/)
**Status:** ready-for-agent
**Blocked by:** nenhum
**Refs:** ADR 0010 (Conector Google), tickets 09/09b (anexos, `app/anexos.py`), ticket 18 (`REVISAR(human)` em `drive_search_read`). Feedback do Toneli em 23/09: pediu "a guia autorizada" do Drive e o modelo respondeu que não lê PDF.

**Problema:** `_legivel` em `app/conectores.py` só aceita Docs, Sheets, Slides e texto. PDF cai em "outros achados" e nunca é baixado. O modelo já lê PDF quando o Usuário anexa (Gemini, `media_resolution` medium), mas não quando o PDF vem do Drive. Guia e boleto costumam ser escaneados: extrair texto no servidor (pypdf) não resolve.

**Decisão (Toneli, 23/09):** o PDF do Drive entra no modelo pelo mesmo caminho do PDF anexado, como arquivo (`BinaryContent`, `application/pdf`, mesma `media_resolution` medium). Alternativa descartada: texto via pypdf (vazio em PDF escaneado). Escrever ADR 0015 com isso.

**What to build:**
- `drive_search_read`: se não houver arquivo de texto legível e houver PDF entre os achados, baixa o primeiro PDF (`alt=media`) e devolve ao modelo como arquivo junto de uma linha de texto (nome, id, outros achados). Use o retorno multimodal de tool do Pydantic AI (`ToolReturn`/`BinaryContent`); confira na versão instalada como ele chega ao Gemini.
- Teto antes de baixar: pedir `size` nos `fields` da busca; PDF acima de 10 MB não baixa e volta como texto explicando o limite. Registrar o teto em DECISOES-AUTONOMAS se escolher outro valor.
- Histórico: os bytes do PDF só vão no turno em que a tool rodou. Nos turnos seguintes, e no histórico persistido/recarregado, o arquivo vira `[arquivo do Drive: nome]`, como `sem_bytes` faz com anexo. Conferir persistência em `chat.py` e a compactação (`compactacao.py`) para não gravar nem reenviar bytes.
- Evento de auditoria existente da tool continua; incluir `mime` e `bytes` no payload se couber sem mudar o schema.
- Atualizar o comentário `REVISAR(human)` da função.

**Aceite:**
- [ ] Teste: busca que acha só PDF devolve à tool um conteúdo com `BinaryContent` `application/pdf` (transporte httpx mockado, `FunctionModel` confere que o arquivo chegou ao modelo).
- [ ] Teste: PDF acima do teto não é baixado (nenhuma chamada `alt=media`) e o retorno explica o limite.
- [ ] Teste: arquivo de texto continua preferido ao PDF (comportamento atual preservado).
- [ ] Teste: turno seguinte / histórico recarregado não carrega os bytes do PDF.
- [ ] ADR 0015 escrito.
- [ ] Uma chamada real ao Gemini (teto: 2) com um PDF pequeno, confirmando que o modelo lê o conteúdo. Registrar no LEDGER.
