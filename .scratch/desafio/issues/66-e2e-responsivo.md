# 66 — Validação end-to-end do responsivo

**Type:** task (web/)
**Status:** resolved
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

## Answer
- `checar-responsivo.mjs --abrir-sidebar` nas 14 rotas de `App.tsx` x 390/768/1440 (vite preview 4186 -> API 8013 com o código atual, Postgres 5433): 0 violações. Todas as screenshots 390 olhadas: sem corte nem sobreposição.
- Fluxos em 390x844 (Brave, playwright-core, script descartável que mede sem isentar o scroller do chat): login, sidebar buscar/abrir/fechar, nova conversa com código + URL longa (streaming e resposta), popover de tools liga/desliga/volta, popovers de modelo e custo, tool calls expandidas, 8 telas pelo nav, tema claro e volta, apagar conversa. Todos OK. Screenshots `.scratch/desafio/screens/66-*`.
- Corrigido em `AppLayout.tsx`: depois de trocar o tema, o menu seguia "Tema claro" no tema claro (`alternarTema` só mexe no classList, nada re-renderizava). Agora força re-render.
- Conta demo igual ao snapshot de antes (settings, tools, conversas, shares); conversa criada apagada. Gemini 1, Tavily/Jev 0 (API subiu sem as chaves). Sem REVISAR(human).
- Tickets sugeridos: (a) nome da tool no cabeçalho do bloco some em 390 com badge do servidor ("stripe_api_d…" repetido, indistinguível); (b) data dos itens de Compartilhados truncada em 390; (c) `Placeholder` (Perfil) com `p-8` fixo, gutter de 32 px no mobile contra 16 px das outras telas.
