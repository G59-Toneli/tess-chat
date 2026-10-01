# 67 — Acabamento mobile: título no header, nome da tool, data, gutter

**Type:** task (web/)
**Status:** resolved
**Blocked by:** 66
**Refs:** `docs/UI-GUIA.md`, Answer dos tickets 63 e 66, `web/scripts/checar-responsivo.mjs`.

**Objetivo:** em 390 px o usuário sabe em que conversa está, distingue cada tool call e lê as datas inteiras.

## Escopo
1. **Título no header** (`web/src/layout/AppLayout.tsx`): abaixo de `md`, entre o `SidebarTrigger` e o avatar, mostrar o título da conversa aberta (em `/c/:id`) ou o nome da tela (nas outras rotas), truncado numa linha. Desktop não muda.
2. **Nome da tool** (`web/src/components/ai-elements/tool.tsx`, `BlocoTool.tsx`): em 390, o cabeçalho do bloco mostra "Stripe" + "stripe_api_d…" repetido e não dá para distinguir as chamadas. Mostrar a parte que distingue: tirar o prefixo do servidor do nome quando o badge já mostra o servidor, e/ou deixar o nome quebrar em até 2 linhas. Escolher, registrar em DECISOES-AUTONOMAS.
3. **Data em Compartilhados** (`web/src/pages/Compartilhados.tsx`): a data do item aparece inteira em 390 (quebra de linha ou formato curto).
4. **Gutter do Perfil** (`web/src/pages/Placeholder.tsx`): 16 px no mobile, como as outras telas (`p-4 md:p-8`).

## Aceite
- `npm run build` limpo.
- `checar-responsivo.mjs` em todas as rotas, 390/768/1440: 0 violações.
- Screenshots 390 em `.scratch/desafio/screens/67-*`: header em `/c/<id>` e em `/config`, conversa com 2+ tool calls do Stripe, `/compartilhados`, `/perfil`. Olhar cada um: nada cortado, nada sobreposto.
- Gemini: 0. Não alterar a Configuração da conta demo.

## Answer
- Header abaixo de `md` mostra o título da Conversa em `/c/:id` ou o nome da tela, truncado (`TituloHeader` em `AppLayout.tsx`). Desktop sem mudança.
- Bloco de tool: tira o slug do servidor do nome quando o badge já mostra ("Stripe" + `api_search`, `api_details`, `api_write`) e quebra em até 2 linhas. Vale também no desktop (DECISOES-AUTONOMAS). `ai-elements/tool.tsx` não mudou: o header usado é o do `BlocoTool.tsx`.
- Compartilhados: data numa linha própria, inteira em 390. Perfil com `p-4 md:p-8`.
- `tsc -b` e `vite build` limpos. `checar-responsivo.mjs --abrir-sidebar` nas 14 rotas + `/c/2dc1e074…` (7 tools Stripe) x 390/768/1440: 0 violações (vite preview 4187 -> API 8014, código atual, Postgres 5433). Screenshots `.scratch/desafio/screens/67-*`, os 390 olhados: nada cortado nem sobreposto.
- Gemini 0. Conta demo sem mudança.
