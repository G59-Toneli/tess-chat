# 39 — `drive_search_read` lista os arquivos mais recentes

**Type:** task (AFK, só api/)
**Status:** ready-for-agent
**Blocked by:** nenhum
**Refs:** ADR 0010, ticket 38 (`drive_search_read` com PDF). Feedback do Toneli em 23/09: "quais últimos arquivos foram adicionados?" devolveu 5 arquivos na ordem de relevância do Drive, não por data. O modelo respondeu como se fossem os mais recentes.

**Problema:** a busca não passa `orderBy` e não mostra data ao modelo. O modelo não tem como responder "últimos", "recentes", "de hoje". A Drive API não aceita `orderBy` junto com `fullText contains`, então a busca por termo não pode simplesmente ganhar ordenação.

**What to build:**
- Consulta vazia (`query` vazia ou só espaços) vira listagem dos 10 arquivos mais recentes: `q = "trashed = false"`, `orderBy = "modifiedTime desc"`. Não lê conteúdo; só lista.
- Toda linha de achado (listagem e "outros achados" da busca por termo) mostra `createdTime` e `modifiedTime` em data curta (`dd/mm/aaaa hh:mm`, fuso America/Sao_Paulo), para o modelo responder "adicionado" ou "modificado" pela data certa.
- Busca por termo continua como está (sem `orderBy`, por causa da restrição do `fullText`).
- Atualizar a descrição da tool que o modelo vê (onde ela mora: `tools.py`, migração 0016 ou `conectores.py`) dizendo que `query` vazia lista os recentes com datas. Se a descrição mora no banco, preferir mudar o default em código; migração só se inevitável (próxima livre: 0019).
- Conferir que o Roteador (ticket 36) não quebra com `query` vazia.

**Aceite:**
- [ ] Teste: `query` vazia chama a Drive API com `orderBy=modifiedTime desc` e sem `fullText`, e devolve a lista com datas, sem baixar arquivo.
- [ ] Teste: busca por termo não envia `orderBy` e mostra as datas nos achados.
- [ ] Teste: comportamento do ticket 38 (PDF, teto de 10 MB, texto preferido) preservado.
- [ ] Sem chamada real a Gemini, Tavily ou Jev.
