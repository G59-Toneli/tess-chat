# 66 — Validação end-to-end do responsivo

**Type:** task (web/)
**Status:** blocked
**Blocked by:** 63, 64, 65
**Refs:** `docs/UI-GUIA.md`, `web/scripts/checar-responsivo.mjs`.

**Objetivo:** provar que o app inteiro funciona em 390 px, com fluxos reais e não só ausência de overflow.

## O que fazer
1. `checar-responsivo.mjs` em todas as rotas de `web/src/App.tsx`, 390/768/1440, contra o build local. Zero violações.
2. Fluxos em 390x844 (playwright-core + Brave), com screenshot de cada passo em `.scratch/desafio/screens/66-*`:
   - login com a conta demo;
   - abrir a sidebar pelo trigger, buscar uma conversa, abrir, confirmar que o Sheet fechou;
   - nova conversa, enviar **1** mensagem curta, ver o streaming e a resposta (**teto: 2 chamadas Gemini**);
   - abrir popover de tools, ligar/desligar uma e voltar ao estado original;
   - navegar por todas as telas pelo nav da sidebar;
   - trocar tema no menu do usuário e voltar para dark;
   - apagar a conversa criada no passo 3.
3. Achou defeito: corrigir se for de uma linha no arquivo dono; senão listar no Answer como ticket novo.

A rodada contra produção (`https://chat.toneli.dev.br`) é do orquestrador, depois do push.

## Aceite
- Script e fluxos passam local.
- Nenhuma mudança residual na conta demo (conversa apagada, tools e Configuração como antes).
