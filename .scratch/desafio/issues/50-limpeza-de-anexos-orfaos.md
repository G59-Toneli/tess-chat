# 50 — Limpeza diária de arquivos de anexo órfãos

**Type:** task (api/ e deploy/cron-tess-chat)
**Status:** resolved
**Blocked by:** nenhum
**Refs:** tickets 09/09b (anexos), 48 (fork duplica arquivo), ADR 0021, `docs/INFRA.md` (disco do VPS chegou a 97% em 03/09; Postgres de produção no mesmo disco). Pedido do Toneli em 23/09.

**Problema:** o arquivo do anexo mora no disco (`attachments_dir`) e a linha em `attachments`. As linhas somem por cascade (apagar Usuário, Conversa ou Mensagem), mas o arquivo fica. Upload que nunca vira Mensagem (`message_id` nulo) também fica para sempre. Cada fork (ticket 48) duplica arquivos. O disco enche e derruba o Postgres de produção.

**Decisão (orquestrador, 23/09, Toneli aprovou o ticket):** uma varredura diária, não hook em cada caminho de exclusão. Motivo: a varredura pega todo caminho, inclusive exclusão manual no banco e cascade que o código não vê; hook por endpoint esquece caminho. Cota de disco por Usuário fica fora (registrar como limite conhecido).

**What to build:**
- Módulo `app/limpeza_anexos.py` com entrada de linha de comando (`python -m app.limpeza_anexos [--dry-run]`):
  1. Apaga arquivo em `attachments_dir` que não tem linha em `attachments` (compara pelo caminho).
  2. Apaga linha + arquivo de anexo com `message_id` nulo criado há mais de 24 h (upload abandonado).
  3. Arquivo com idade menor que 1 h nunca é apagado (upload em andamento, corrida com o passo 1).
  4. Evento de auditoria `attachments_swept` com contagens e bytes liberados. `--dry-run` só lista e não grava.
- Nunca segue symlink nem sai de `attachments_dir`.
- `deploy/cron-tess-chat`: linha diária (ex.: 03:45, depois do backup) rodando `docker compose -f /opt/tess-chat/deploy/docker-compose.yml exec -T app python -m app.limpeza_anexos` com log em `/opt/tess-chat/backups/limpeza.log`. Exceção à regra de não tocar `deploy/`: só este arquivo. O orquestrador instala no VPS.
- `docs/INFRA.md` ganha uma linha sobre a limpeza (exceção à regra de não tocar: só essa linha).

**Aceite:**
- [ ] Teste: arquivo sem linha e com mais de 1 h é apagado; arquivo com linha fica.
- [ ] Teste: anexo sem Mensagem com mais de 24 h some (linha e arquivo); com menos de 24 h fica.
- [ ] Teste: arquivo com menos de 1 h fica mesmo sem linha.
- [ ] Teste: `--dry-run` não apaga nada e não grava evento.
- [ ] Teste: apagar uma Conversa com anexo e rodar a varredura libera o arquivo.
- [ ] Sem chamada real a Gemini, Tavily ou Jev.

## Answer
- `app/limpeza_anexos.py`: `varrer()` apaga linhas de upload sem Mensagem há 24 h (commit antes de tocar disco) e depois todo arquivo do primeiro nível de `attachments_dir` sem linha e com mais de 1 h. Pula symlink e subpasta. Evento `attachments_swept` com `files_deleted`, `rows_deleted`, `bytes_freed`. `--dry-run` só lista.
- Cron às 03:45 em `deploy/cron-tess-chat` (`exec -T app`, WORKDIR `/app/api`), log em `backups/limpeza.log`; linha em `docs/INFRA.md`. Orquestrador instala no VPS.
- 6 testes passam; o de symlink fica skip no Windows (sem permissão de criar link) e roda no Linux.
- Limite conhecido: sem cota de disco por Usuário. Entre o cascade e a varredura o arquivo fica até 24 h no disco.
ordem linha-antes-de-arquivo).
