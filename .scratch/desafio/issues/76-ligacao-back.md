# 76 — Ligação no backend: ticket, proxy WebSocket, crédito, auditoria

**Type:** task (api/)
**Status:** resolved
**Blocked by:** 75
**Refs:** ADR 0026, 0027, 0023 (vaga de turno), 0004/0019 (reserva e acerto), 0007 (auditoria). `docs/PROTOCOLO-LIGACAO.md` (contrato, obrigatório). `spike/live/RESULTADO.md` (nomes reais do SDK, obrigatório).

**Objetivo:** o servidor é dono da Ligação. O browser só fala o protocolo.

## Escopo
Código novo em `api/app/voz.py` (router incluído no `main.py`). **Não editar `api/app/chat.py`**: se precisar de algo de lá, importar. Pode editar `turnos.py`, `credito.py`, `config.py` com mudança mínima.
1. `POST /api/voz/ticket` e `WS /api/voz/ws` conforme o protocolo. Ticket em memória, uso único, 30 s.
2. `conectar_gemini()` injetável (padrão `dependency_overrides` ou função substituível). O resto do módulo não conhece o objeto concreto do SDK.
3. Relay nos dois sentidos com duas tasks asyncio (browser→Gemini, Gemini→browser). O fim de uma encerra a outra.
4. A Ligação ocupa a vaga de turno da Conversa (`turnos.reservar`). Uma por Usuário, teto global 3.
5. Limite de 540 s (config). No limite: `fim` com motivo `limite`.
6. Crédito: reserva de 9 min no início; acerto pelo `usageMetadata` no fim; preço de tabela mesmo na chave free. Tabela de Preço ganha o `gemini-3.8-live` com modalidades (próxima migração livre: **0024**).
7. Auditoria: `voice_call_started`, `voice_call_ended` (duração, motivo, tokens por modalidade, custo), `screen_share_started`, `screen_share_stopped`. Não por frame.
8. Config nova `GEMINI_LIVE_API_KEY` (em `config.py` e `.env.example`), mais modelo, voz, limite, fps e resolução como config.
9. Prompt: system prompt do chat + adendo de voz do ADR 0026.
10. Fim único (protocolo seção 5), com `finally`.

A transcrição no histórico e o histórico na Ligação são o ticket 77. Aqui, só guardar as falas em memória na sessão.

## Aceite (pytest com Gemini falso, sem chamada real)
- Ticket inválido, expirado ou reusado → 4401.
- Sem espaço no Cap → 402 no ticket; nada no Ledger.
- Segunda Ligação do mesmo Usuário → 409. Texto `POST /api/chat/{cid}` durante a Ligação → 409.
- Áudio e frame do browser chegam ao Gemini falso; áudio e transcrição do falso chegam ao browser; `interrupted` vira `interrompido`.
- Limite (com limite curto no teste) → `fim` `limite`, vaga liberada.
- Desligar e queda do browser → Ledger com o acerto do uso falso, `voice_call_ended` com o motivo certo, vaga liberada.
- `REVISAR(human)` em: o relay, a validação do ticket, o fim único, o acerto de crédito.
- Chamadas reais: no máximo 2 sessões curtas para smoke local. LEDGER.

## Paradas de estudo
Adicione aqui 4 a 6 entradas no formato do `docs/ESTUDO-VOZ.md`. Obrigatórias: por que proxy e não token efêmero; como o ticket funciona e por que não JWT na URL; por que a Ligação ocupa a vaga de turno; como o relay de duas tasks encerra junto.

### 1. Proxy no servidor, não token efêmero no browser
- **Conceito:** o browser abre um WebSocket com o FastAPI, e o FastAPI abre outro com o Gemini Live. Cada byte passa pelo servidor nos dois sentidos.
- **Por quê:** com token efêmero, o browser falaria direto com o Google e o servidor não veria o `usage_metadata`. O Cap e a auditoria dependeriam do que o browser reporta, e o browser pode mentir. Caiu o token efêmero (menos código, um salto a menos).
- **Onde:** `api/app/voz.py:285` (`_relay`), `api/app/voz.py:80` (`conectar_gemini`).
- **Pergunta de revisão:** "Por que não deixar o browser falar direto com o Gemini?"
  **Resposta:** Porque o custo e a auditoria são obrigatórios e o servidor precisa ver o uso real. No proxy, o servidor lê o `usage_metadata` de cada turno e grava o acerto no Ledger. O preço é um salto a mais, dezenas de ms contra centenas do modelo.

### 2. Ticket de Ligação em vez de JWT na URL
- **Conceito:** o browser não manda header no WebSocket. Então ele pede um ticket com o Bearer normal (`POST /api/voz/ticket`) e conecta com `?ticket=`. O ticket vive em memória, vale 30 s e some no primeiro uso.
- **Por quê:** a URL fica no log do nginx. Um JWT ali vale 24 h para quem ler o log. O ticket no log já está gasto. O `pop` acontece antes de checar a validade: nem o ticket expirado aceita segunda tentativa. JWT na URL caiu por isso.
- **Onde:** `api/app/voz.py:231` (`_consumir`).
- **Pergunta de revisão:** "Como você autentica um WebSocket se o browser não manda Authorization?"
  **Resposta:** Com um ticket de uso único pedido por uma rota HTTP autenticada. Ele vale 30 s e só cobre o intervalo até o upgrade. Vazar o ticket depois do uso não dá acesso a nada.

### 3. A Ligação ocupa a vaga de turno da Conversa
- **Conceito:** a Ligação chama `turnos.reservar(cid)`, o mesmo registro do turno de texto (ADR 0023). Enquanto ela dura, `POST /api/chat/{cid}` recebe 409.
- **Por quê:** duas respostas simultâneas na mesma Conversa brigam pelo histórico e pelo Crédito. Reusar a vaga dá o 409 de graça, sem lock novo. A checagem e o registro acontecem sem `await` entre eles, então dois WebSockets não passam juntos.
- **Onde:** `api/app/voz.py:248`.
- **Pergunta de revisão:** "O que acontece se o usuário manda texto durante a ligação?"
  **Resposta:** Recebe 409, o mesmo de um turno em andamento. A Ligação é um turno longo. A vaga sai no fim único antes de o servidor mandar o `fim`, então o browser já pode mandar texto quando recebe o `fim`.

### 4. Relay de duas tasks que encerram juntas
- **Conceito:** uma task lê do browser e manda para o Gemini; outra lê do Gemini e manda para o browser. `asyncio.wait(FIRST_COMPLETED, timeout=540)` acorda na primeira que acaba ou no limite. A outra é cancelada e esperada.
- **Por quê:** cada lado fala quando quer; um laço só travaria esperando um dos dois. Cancelar e esperar (`gather`) evita task órfã escrevendo num WebSocket fechado. O motivo sai de quem acabou: `desligou` ou `queda` devolvidos pela task, exceção vira `erro`, timeout vira `limite`.
- **Onde:** `api/app/voz.py:285`.
- **Pergunta de revisão:** "Se o usuário fecha a aba, como o servidor para de falar com o Gemini?"
  **Resposta:** A task do browser recebe `websocket.disconnect` e devolve `queda`. O `wait` acorda, cancela a task do Gemini e o `finally` roda o fim único: acerto, auditoria, vaga liberada. A sessão Gemini fecha ao sair do `async with`.

### 5. Fim único e acerto pela soma dos turnos
- **Conceito:** todo fim passa por `_encerrar`, chamado do `finally`. Ele faz o acerto, emite `voice_call_ended` e libera a vaga, nessa ordem. O acerto soma o `usage_metadata` de cada turno, por modalidade, ao preço de tabela.
- **Por quê:** quatro caminhos de fim com código próprio esquecem um passo e deixam 409 eterno. O Gemini manda um uso por turno, e cada turno cobra o contexto de novo, então a soma é o custo. Sem nenhum uso reportado, estima pela duração (25 tokens/s).
- **Onde:** `api/app/voz.py:441` (`_encerrar`), `api/app/voz.py:409` (`_acertar`).
- **Pergunta de revisão:** "Como você cobra uma ligação que a chave free não cobra?"
  **Resposta:** Pelo preço de tabela do modelo pago, com cada modalidade no seu preço: áudio, imagem, texto e pensamento. O Crédito mede quanto custaria, então o Cap continua funcionando. A reserva de 9 min no ticket garante que a Ligação inteira cabe no Cap.

## Answer
`api/app/voz.py`: `POST /api/voz/ticket` e `WS /api/voz/ws` conforme o protocolo, relay de duas tasks, vaga de turno, teto 3, limite de 540 s, reserva de 9 min e acerto por modalidade (migração 0024), 4 Eventos de auditoria, fim único no `finally`. 10 testes com Gemini falso em `tests/test_voz.py`. Smoke real: 2 sessões free (desligar e queda), leu a tela, latência 503 e 626 ms (host local), Ledger e `voice_call_ended` gravados.
Ressalvas: o prompt é só o adendo de voz (o do chat só fala de tools); `pronto` segue o protocolo sem fps e resolução; a linha do Ledger da Ligação aparece como `compactacao` no custo da Conversa; `GET /api/chat/{cid}/stream` durante a Ligação fica aberto até o fim. Detalhes em DECISOES-AUTONOMAS.
`REVISAR(human)`: `_consumir`, `_relay`, `_acertar`, `_encerrar`.
