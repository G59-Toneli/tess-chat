# 77 — Falas da Ligação no histórico e histórico na Ligação

**Type:** task (api/ + web/)
**Status:** blocked
**Blocked by:** 76
**Refs:** ADR 0026. Q4 e Q21 do grilling de 28/09. É o primeiro item a cair se o prazo apertar.

**Objetivo:** a Ligação continua a Conversa nos dois sentidos.

## Escopo
1. **Falas → Mensagens.** No fim único da Ligação, gravar as falas como Mensagens da Conversa, um par usuário/assistente por troca, no formato de partes do AI SDK que o chat já usa. Marca de Ligação nos metadados da parte (formato livre; registrar em DECISOES-AUTONOMAS). Mensagens vazias não entram.
2. **Front:** a Mensagem com marca de Ligação mostra um indicador discreto ("por voz"). Ao desligar, o histórico recarrega e as falas aparecem.
3. **Histórico → Ligação.** No início da Ligação, enviar ao Gemini o texto das últimas Mensagens da Conversa (só texto, sem imagem e PDF), teto ~4k tokens (config), mais recentes primeiro no corte.
4. As Mensagens da Ligação entram na Compactação como qualquer Mensagem.

## Aceite
- pytest com Gemini falso: depois de desligar, `/messages` tem os pares com a marca; o Gemini falso recebeu o histórico em texto, dentro do teto; imagem do histórico não vai.
- Front: `npm run build` limpo; screenshot no Brave (dark, 1440x900) de uma Conversa com Mensagens por voz em `.scratch/desafio/screens/77-*`.
- `REVISAR(human)` na montagem do histórico e na gravação das falas.
- Chamadas reais: 0.

## Paradas de estudo
2 a 3 entradas no formato do `docs/ESTUDO-VOZ.md`. Obrigatória: por que um par por troca e não um bloco único.
