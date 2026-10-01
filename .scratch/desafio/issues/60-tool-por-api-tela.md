# 60 — Tool por API (tela): cadastro guiado com teste

**Type:** task (web/)
**Status:** resolved
**Blocked by:** 59
**Refs:** ticket 59, ADR 0024, `docs/UI-GUIA.md`, padrão visual de `web/src/pages/Mcp.tsx` (ticket 56).

**Objetivo:** um usuário que não sabe o que é JSON Schema cadastra uma tool em menos de 1 minuto.

## Tela
- A seção "Tools por API" fica em `/tools`. Se `/tools` estiver cheia, cria `/api-tools` com um link no nav, em "Extensões". Decide pelo UI-GUIA e registra.
- **Modelos:** 3 cards (ViaCEP, Open-Meteo, CNPJ), cada um com uma linha do que faz e o botão "Usar". O botão preenche o formulário inteiro, inclusive os valores de exemplo.
- **Formulário em passos curtos, na mesma tela:**
  1. **URL e método.** Ao digitar a URL, cada `{param}` detectado vira uma linha na lista de parâmetros, na hora.
  2. **Parâmetros.** Para cada um: descrição (obrigatória, com placeholder de exemplo), tipo (select com padrão texto), obrigatório (switch ligado por padrão) e valor de exemplo.
  3. **Autenticação.** As opções são Nenhuma, Chave no header e Token Bearer. O campo do segredo é do tipo password, com o texto "Guardado cifrado. Nunca volta para a tela."
  4. **Nome e descrição.** O nome é sugerido a partir do host e do path. A descrição tem um contador e um exemplo ("Busca o endereço de um CEP brasileiro").
  5. **Corpo JSON**, só no POST, num textarea com validação de JSON ao vivo.
- **Testar:** chama `/api/api-tools/testar` e mostra o status, o tempo e a resposta formatada, cortada e rolável.
- **Salvar:** fica desabilitado até existir um teste 2xx com a definição atual. Mudar qualquer campo invalida o teste.
- **Lista "Minhas tools por API":** um card por tool com nome, método, host, número de parâmetros e o botão Remover.
- As tools novas aparecem no pill de tools da conversa, como já acontece com as de MCP. Confira.

## Aceite
- `npm run build` limpo.
- Screenshots no Brave (dark, 1440x900, sem overflow), fora do git:
  - modelo ViaCEP aplicado e testado, com a resposta visível;
  - erro de teste 404 com a mensagem;
  - lista com 1 tool.
- E2E local com a API do ticket 59 numa porta própria: cadastrar o ViaCEP pelo modelo e conferir que a tool aparece no pill de uma conversa. Chamada real ao ViaCEP é permitida (grátis). Gemini: 0.

## Answer
- Tela nova `/api-tools` ("Tools por API" em Extensões): 3 modelos com "Usar", formulário em 5 passos (parâmetros saem dos `{param}` da URL e do corpo na hora), Testar com status, ms e resposta formatada rolável, Salvar só com teste 2xx da definição atual, lista com Remover.
- Pill da conversa: tool `api_xxxx_<nome>` aparece com badge `api` (igual ao `mcp`), conferido no `/` e numa conversa criada por API.
- E2E no Brave com a API na 8007: modelo ViaCEP testado (200), 404 com o HTML do ViaCEP, cadastro, pill. 4 chamadas ViaCEP, 0 Gemini. Screenshots `.scratch/desafio/screens/60-*.png`.
- Ressalva: não há vitest no `web/`; `nomeSugerido` e `placeholders` só foram checados pelo E2E.
