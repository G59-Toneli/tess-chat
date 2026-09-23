# 07 — Front base: login, lista de conversas, chat streaming

**Type:** task (AFK)
**Status:** resolved
**Blocked by:** 06
**Refs:** ADR 0002. `docs/UI-GUIA.md` (obrigatório). Resultado do spike (hipótese 3).

**What to build:** `web/` com Vite + React + shadcn + AI Elements (ou fallback do spike). Telas: login/cadastro, sidebar de conversas, chat com `useChat`. Build copiado para o container do FastAPI e servido em `/`. UI em pt-BR.

**Aceite:**
- [x] Fluxo completo no browser: cadastrar, criar conversa, mandar mensagem, ver stream, recarregar e ver histórico.
- [x] `docker build` gera uma imagem só que serve front e API.

**Do spike:** `shadcn init -b radix` (Base UI quebra o `prompt-input`). Sem `baseUrl` no tsconfig (TS 6). Envolver o app em `TooltipProvider`. Code-split só se o bundle de 1,6 MB incomodar.

**Acabamento obrigatório (revisão do orquestrador nas telas do 07a):** o scaffold está funcional mas cru. Neste ticket: nome do app "Tess Chat" com ícone no header e no login; login em card centralizado com título, subtítulo, alternar cadastro, botão "entrar com conta demo" que preenche as credenciais; sidebar com avatar/iniciais, busca, agrupamento por data (hoje, ontem, 7 dias), menu por conversa (renomear, apagar com confirmação); área de chat vazia com estado "comece uma conversa" e 3 sugestões clicáveis; indicador de "pensando" antes do primeiro token; mensagens com avatar e horário; erro do provedor como toast em pt-BR. Seguir `docs/UI-GUIA.md` e olhar https://www.beautifului.dev/ para loading e "digitando". Screenshots dark de login, lista vazia, conversa com stream e erro.

## Answer
Front ligado na API real: login e cadastro com JWT no `localStorage`, sidebar com busca, grupos por data, renomear e apagar com confirmação, chat com `useChat` em `/api/chat/{id}`, histórico do banco ao recarregar. Acabamento do ticket feito: nome Tess Chat, conta demo, estado vazio com 3 sugestões, indicador "pensando", avatar e horário, erro do provedor como toast com "Tentar de novo".
Verificado no Brave: cadastrar, criar conversa, stream, recarregar e ver histórico (1 chamada real ao Gemini); erro com chave inválida por env (502, toast). `docker build` gera uma imagem que serve `/`, `/health`, login e `/api`. Screenshots em `.scratch/desafio/screens/07-*.png`.
Ressalvas: a resposta curta chegou inteira antes do screenshot, então `07-conversa-stream.png` mostra o fim do stream; o "pensando" está em `07-pensando.png`. A credencial demo está fixa no front.
REVISAR(human): `agruparPorData` em `web/src/lib/datas.ts` e o fluxo da primeira mensagem em `web/src/pages/Chat.tsx`.
