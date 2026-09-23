# 12 — Compactação automática do histórico

**Type:** task (AFK + HITL)
**Status:** resolved
**Blocked by:** 08
**Refs:** ADR 0006.

**What to build:** `ProcessHistory` que, quando os tokens de entrada do turno anterior passam do limiar da Configuração, resume as mensagens antigas com flash-lite mantendo os últimos N turnos literais, sem separar tool-call de resultado. Resumo persistido em `summaries` (conversa, até_mensagem_id, texto, tokens). Próximas chamadas usam resumo + mensagens após o corte. Evento `compaction` com tokens antes/depois. Débito do resumo no ledger. Front: marcador "histórico compactado aqui".

**HITL:** a função `should_compact(usage, settings) -> bool` fica com `TODO(human)`. Testes primeiro.

**Aceite:**
- [x] Com limiar 2.000 tokens, a 4ª mensagem de uma conversa longa dispara compactação sem erro e a resposta continua coerente com o começo da conversa.
- [x] Mensagens originais continuam na UI e no banco.
- [x] Teste: nenhum resumo corta entre tool-call e resultado.

## Answer
`ProcessHistory` em `app/compactacao.py`: se o input do turno anterior passa de `compactacao_limiar`, resume com flash-lite tudo antes dos últimos 2 turnos, grava em `summaries` (migração 0009), debita no Ledger e emite `compaction` com tokens antes/depois reais. Próximos turnos usam Resumo + Mensagens depois do corte. Front: `MarcadorCompactacao` mostra "Histórico compactado aqui".
Manual com limiar 2.000 (3 turnos semeados + 2 reais, 3 chamadas Gemini): compactou 3.000 → 309 tokens e o 5º turno lembrou nome, cidade, cachorro, prazo e orçamento do 1º. Screenshot: `.scratch/desafio/screens/12-chat-marcador.png`.
Ressalvas: o input do turno soma todos os requests (tool loop conta dobrado); marcador do turno ao vivo só aparece ao recarregar; limiar e N ficam em `settings` até o 14.
REVISAR(human): `should_compact`, `ponto_de_corte`, `Compactacao.processar`.
