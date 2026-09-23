# ADR 0023 — Turno em background, buffer em memória, pergunta gravada no início

**Status:** aceito, 2026-09-23. Revisa a decisão do ticket 06 em `DECISOES-AUTONOMAS.md` ("usuário e assistente gravados juntos").

## Contexto
O turno rodava dentro da request HTTP. Trocar de tela ou dar F5 fazia o `useChat` chamar `stop()`. Então o Starlette cancelava o run no `http.disconnect`. `_persistir` só rodava no fim com sucesso, então o turno sumia: nenhuma Mensagem, nenhum débito no Ledger, nenhum `llm_call`. As tools MCP já tinham executado os efeitos colaterais. O Toneli decidiu em 23/09: a pergunta é gravada no início; o botão Parar cancela no servidor e grava o parcial; task asyncio no mesmo processo, sem Redis.

## Decisão
1. **`app/turnos.py`: registro `{cid: TurnoAtivo}` no módulo.** `TurnoAtivo` guarda a `asyncio.Task` (referência forte), a lista de chunks SSE já codificados, um `asyncio.Condition` para os leitores e um `CancellationToken` do Pydantic AI.
2. **`POST /api/chat/{cid}`.** Ocupa a vaga antes de qualquer `await`: turno ativo dá 409. Faz na request o que precisa dela: valida o body, reserva o crédito, chama o Roteador e grava a pergunta (`message_sent`) com commit. Então cria `asyncio.create_task(rodar_turno(...))`. A task consome o run e escreve no buffer. A `StreamingResponse` só lê o buffer. O `http.disconnect` mata só o leitor.
3. **502 preservado.** O 1º evento do modelo é esperado dentro da task. Um `Future` (`pronto`) devolve ao POST `None` (abre o stream) ou a resposta 502.
4. **`GET /api/chat/{cid}/stream`.** 204 sem turno ativo. Com turno ativo, replay desde o chunk 0 (inclui o `start` com o message id) e depois tail. É o contrato do `DefaultChatTransport` com `resume: true`.
5. **`POST /api/chat/{cid}/parar`.** Chama `token.cancel()`, que vira `RunCancelled`. O `on_cancel` grava o parcial, cobra o uso real e emite `turn_stopped`. Esse é o mesmo caminho do corte do `ComTeto`. `Task.cancel()` foi descartado: vira `CancelledError`, o `on_cancel` não roda e o parcial se perde. O POST espera o turno gravar (teto de 10 s).
6. **`_persistir` grava só o que vem depois da pergunta:** assistente, Ledger, auditoria. O turno sai do registro depois do `_persistir`. Então quem lê o fim do stream já pode mandar o próximo POST.
7. **"Tentar de novo" (`regenerate-message`) com a última Mensagem `user` sem resposta** reusa essa pergunta. Isso evita a pergunta duplicada.

### Alternativas descartadas
- **Redis pub/sub ou fila (arq, Celery).** O deploy é um uvicorn sem `--workers`. Um processo não precisa de broker. Com multi-worker, o buffer vai para Redis e o 409 vira lock no banco.
- **Persistir cada passo do loop.** Sobrevive a restart, mas pede Mensagem parcial no banco, com merge no fim. É o próximo degrau.
- **Continuar gravando pergunta e resposta juntas.** Ao voltar para a tela, a pergunta sumia até o turno acabar.

## Consequências
- Restart do processo ou deploy do CI no meio do turno ainda perde o turno. A pergunta fica sem resposta.
- Turno que falha deixa a pergunta sem resposta no histórico. O próximo turno manda duas Mensagens `user` seguidas.
- `corte_atual` acha a pergunta do turno que compactou pela 1ª resposta depois do Resumo. Isso vale para os dados antigos e os novos.
- Janela curta: o `/messages` lê antes do commit do assistente, e o `/stream` chega depois de o turno sair do registro. Nesse caso a resposta só aparece no próximo reload.
- O texto pendente em `/` (`Map` em `Chat.tsx`) se perde no reload antes do envio.
- O Cap não é checado entre passos do loop (problema anterior, fora deste ADR).
