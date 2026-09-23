# 40 — Descrição de `drive_search_read` volta a ter uma fonte só (banco)

**Type:** task (AFK, só api/)
**Status:** ready-for-agent
**Blocked by:** nenhum
**Refs:** ticket 39 (`conectores.DESCRICOES`), migrações 0012 (registro das tools do Google) e 0016 (`descricao_usuario`).

**Problema:** o ticket 39 pôs a descrição nova de `drive_search_read` em `conectores.DESCRICOES`, que sobrepõe `tools.descricao` só na montagem do toolset (`tools.py`). A tela Conectores/Tools e o Roteador continuam lendo a descrição antiga do banco. Duas fontes da verdade para o mesmo texto.

**What to build:**
- Migração 0019: `UPDATE tools SET descricao = <texto atual de conectores.DESCRICOES["drive_search_read"]>, descricao_usuario = <voz do produto mencionando PDF e arquivos recentes, curto como os da 0016>` onde `nome = 'drive_search_read'`. `downgrade` volta os textos anteriores (copiar da 0012 e da 0016).
- Remover `conectores.DESCRICOES` e o `.get` em `tools.py`: o toolset volta a usar `tool.descricao` como as outras tools.
- Se houver seed em código que recria as tools do Google (fora das migrações), atualizar o texto lá também.
- Não mexer em `roteador.DESCRICOES`: é a sobreposição validada no spike (hipótese 9), conceito diferente.
- Tirar a linha do ticket 39 em DECISOES-AUTONOMAS ou marcar como superada pelo 40.

**Aceite:**
- [ ] Teste: depois das migrações, o toolset entrega ao modelo a descrição que menciona query vazia e recentes, lida do banco.
- [ ] Teste: a API que a tela usa para listar tools devolve a `descricao_usuario` nova de `drive_search_read`.
- [ ] `alembic upgrade head` e `downgrade -1` limpos no Postgres local.
- [ ] Sem chamada real a Gemini, Tavily ou Jev.
