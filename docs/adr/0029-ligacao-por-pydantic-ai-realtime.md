# ADR 0029 — Ligação pelo `pydantic_ai.realtime`: tentada e rejeitada

**Status:** rejeitado, 2026-09-30. Corrige a premissa do ADR 0026, mas mantém a decisão dele: a Ligação segue no SDK `google-genai` direto.

## Contexto
O ADR 0026 escreveu: "a Ligação usa o SDK `google-genai` direto, porque o Pydantic AI não tem abstração para a Live API". A premissa era falsa. O `pydantic-ai-slim==2.47.0`, fixado no `api/pyproject.toml` desde 22/09, já traz `pydantic_ai.realtime`: `RealtimeSession`, provedor Gemini Live em `realtime/google.py`, Frame como `BinaryImage`, sliding window, transcrição das duas falas, `usage` acumulado por modalidade e `ReconnectPolicy`. A pesquisa de 28/09 olhou a doc web, não o pacote instalado.

A migração tinha dois ganhos: um jeito só de falar com o modelo (ADR 0001) e reconexão pronta. Toneli pediu a migração em 30/09 (issue #2, ticket 87).

## O que foi feito
- O módulo cobriu tudo que a Ligação usa, sem gambiarra: uso separado por modalidade (`details['{modalidade}_{prompt|response}_tokens']`, `thoughts_tokens`), PCM 16 kHz e JPEG sem recodificar, `interrupted` como `RealtimeResponseInterruptedEvent`, transcrição acumulada, sessão sem tools, voz, VAD, sliding window, `thinking` e modelo falso injetável por `GoogleProvider(client=...)`.
- A migração ficou pronta e passou nos testes: `test_voz.py` 17 de 17, e2e com Gemini roteirizado 11 de 11, suíte sem regressão.

## Por que caiu
No smoke real, com Frame e a mesma harness (`web/scripts/smoke-ligacao-prod.mjs`, servidor local, Brave, chave free), o caminho novo leu a tela 2 de 6 vezes e o antigo 5 de 5. Nas 4 falhas, o Gemini só contou uns 7 s de áudio depois de 25 a 37 s de relógio, e não chegou a responder a pergunta. Sem Frame, o caminho novo funcionou (1 de 1).

O que sai da máquina foi comparado nos dois caminhos e é idêntico: `LiveConnectConfig`, JSON de `setup`, headers do handshake, tipos, tamanho e ritmo das mensagens, e vazão contra um Gemini falso local. A causa não foi achada. Pode estar no socket ou no TCP, ou ser variação do Gemini que caiu sempre no caminho novo (INFERIDO).

O ganho era de arquitetura, invisível para o usuário. O custo era uma Ligação que falha com tela sem causa conhecida, perto da entrega. O caminho antigo funciona em produção.

### Alternativa escolhida
- **Manter o SDK `google-genai` direto (ADR 0026).** Funciona, está testado e em produção. Custo: dois jeitos de falar com o modelo, e session resumption continua para escrever à mão.

## Consequências
- Nenhuma mudança de código. A tentativa não foi guardada em branch.
- Para retomar: medir o buffer de escrita e o `drain` do WebSocket numa Ligação que falhe, com Frame. É o único ponto entre o `send()` e o Gemini que não foi medido. Depois, repetir o placar alternando os dois caminhos.
- Lição: antes de escrever "a lib não tem X", ler o pacote instalado na versão fixada.
