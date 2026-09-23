# 55 — Turno em background com retomada

**Type:** task (api/ + web/)
**Status:** resolved
**Refs:** pedido do Toneli em 23/09. Plano aprovado: `C:\Users\Admin\.claude\plans\cara-acabei-de-perceber-playful-quasar.md` (leia inteiro). Revisa `docs/DECISOES-AUTONOMAS.md:18` (ticket 06).

**Problema:** o turno roda dentro da request HTTP (`api/app/chat.py:386-397`). Se o usuário troca de tela ou recarrega, o `useChat` chama `stop()` no unmount e o Starlette cancela o run no `http.disconnect`. `_persistir` só roda no fim com sucesso, então o turno some: nenhuma Mensagem, nenhum débito no Ledger, nenhum `llm_call`. As tools MCP já executaram.

**Decisões (Toneli, 23/09):**
- A mensagem do usuário é gravada no início do turno.
- O botão Parar cancela o run no servidor e grava o parcial, pelo mesmo caminho do corte do `ComTeto` (`on_cancel`).
- Task asyncio no mesmo processo, buffer em memória. Sem Redis/fila. Deploy é um uvicorn só.

**Aceite:**
- `POST /api/chat/{cid}` roda o turno numa `asyncio.Task` desacoplada da request. Desconectar o cliente não cancela o run. Segundo POST com turno ativo → 409.
- `GET /api/chat/{cid}/stream`: 204 sem turno ativo; senão replay dos chunks SSE desde o início + tail. Contrato do `DefaultChatTransport` do AI SDK.
- `POST /api/chat/{cid}/parar`: cancela e grava o parcial + cobrança.
- Front: `resume: true` no `useChat`; `onParar` chama `/parar` e depois `stop()`.
- Testes de integração com modelo fake (sem Gemini real): desconexão no meio → `/messages` tem usuário + assistente e o Ledger tem o débito; `/stream` replay e 204; 409; `/parar` grava parcial.
- ADR 0023 novo. Atualiza `DECISOES-AUTONOMAS.md:18`, `ESTRUTURA.md`, `MOTIVACOES.md`. `REVISAR(human)` em `rodar_turno` e no leitor do buffer.
- Validado no browser local (Brave): mandar mensagem, trocar para `/creditos`, voltar; repetir com F5. Screenshot em `screens/55-*.png`.

## Answer
- O turno roda numa `asyncio.Task` (`app/turnos.py` + `rodar_turno` em `chat.py`). O POST lê um buffer em memória. Desconectar não cancela o turno. O segundo POST dá 409. `GET /stream` faz replay e tail, ou 204. `POST /parar` cancela pelo `CancellationToken` e grava o parcial com `turn_stopped`.
- A pergunta é gravada no início. `_persistir` grava só a resposta. O "Tentar de novo" reusa a pergunta sem resposta. `corte_atual` foi ajustado para a nova ordem.
- Front: `resume: true`, `prepareReconnectToStreamRequest`, porque o padrão iria para `/api/chat/{id}/{id}/stream`. O Parar chama `/parar` e depois `stop()`. Validado no Brave: troca para `/creditos` e F5 no meio do turno, com 3 chamadas Gemini. Conversa nova de `/` não retoma (`resume` congelado): o 204 derrubaria o status do envio.
- Ressalvas no ADR 0023: um restart perde o turno; um turno que falha deixa a pergunta sem resposta; existe uma janela curta entre `/messages` e `/stream`.
- `REVISAR(human)` em `rodar_turno`, `TurnoAtivo.ler`, `_persistir` e `corte_atual`.
