# Para o Toneli de manhã

Itens que precisam de você. O orquestrador acrescenta aqui durante a noite.

- [x] **Trocar o `GITHUB_PAT`.** Vazou em texto aberto no log local da sessão do agente do ticket 03. Não foi para o repo. Gere um novo, atualize o `.env`. Depois, recadastre o GitHub em `/mcp`: o header fica cifrado no banco com o PAT velho (ticket 17).
- [x] `TAVILY_API_KEY` adicionada (free, 1.000 créditos/mês). Testes do ticket 10 usam resposta gravada, não a API.
- [ ] Ler `docs/DECISOES-AUTONOMAS.md`: decisões que os agentes tomaram sozinhos. Já tem a do JWT_SECRET e DEMO_PASSWORD com default de dev.
- [ ] Ler os `REVISAR(human)` no código: `grep -rn "REVISAR(human)" api/`. São as funções que você ia escrever e que caem na entrevista.
- [x] SSH do VPS e registro A `chat.toneli.dev.br` feitos (23/09). Produção em https://chat.toneli.dev.br com HTTPS e CI.
- [x] Projeto OAuth no Google feito e testado (23/09 ~03:00). `GOOGLE_CLIENT_ID` e `GOOGLE_CLIENT_SECRET` no `.env`. JSON do client em `C:ProjectsGoogleJsonDesafio` (fora do repo).
- [x] **Validar o Conector Google (ticket 18, aceites 1 e 2).** O consentimento pede seu login Google, então o agente testou só com Google mockado.
  1. Confira no `.env`: `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` e `CONNECTORS_KEY` (o agente gerou). Não troque a `CONNECTORS_KEY` depois de conectar.
  2. `cd api && uv run alembic upgrade head` (migração 0012).
  3. `cd web && npm run build`. O callback volta para `http://localhost:8000/conectores`, não para o Vite.
  4. `cd api && uv run uvicorn app.main:app --port 8000`. Abra `http://localhost:8000`, entre com sua conta.
  5. Menu Conectores > Conectar Google. Aceite Gmail e Drive. A tela volta com "Google conectado".
  6. Nova conversa: "qual meu último e-mail sobre <assunto real>?". Esperado: tool `gmail_search` no bloco da tool e resposta com remetente e assunto reais.
  7. "resume o arquivo <nome de um Google Doc seu> do meu Drive". Esperado: tool `drive_search_read` e resumo do conteúdo.
  8. Auditoria: eventos `connector_linked` e `tool_call`. Revogar em Conectores gera `connector_revoked`.
  9. Produção: no `.env` do deploy, `PUBLIC_BASE_URL=https://chat.toneli.dev.br` e uma `CONNECTORS_KEY` própria.
- [x] **Validar o envio de e-mail com confirmação (ticket 25, ADR 0013).**
  1. GCP > APIs e serviços > Tela de consentimento OAuth > Escopos: adicione `https://www.googleapis.com/auth/gmail.send`. Salve. (App em Testing: seu e-mail continua na lista de testadores.)
  2. `cd api && uv run alembic upgrade head` (aplica a migração 0014).
  3. Suba a app. Em `/conectores` aparece "Reconecte para enviar e-mails". Clique em Reconectar e aceite a permissão de envio. O selo "Gmail (envio com confirmação)" aparece.
  4. Nova conversa. No seletor de tools, ligue `gmail_send` (nasce desligada).
  5. Peça: "responde o último e-mail do X dizendo que confirmo a reunião". Esperado: `gmail_search`, `gmail_read`, depois um cartão "Rascunho de e-mail" com Para, Assunto, corpo e os botões Enviar e Descartar.
  6. Digite "pode enviar" no chat. Esperado: nada sai; o cartão continua "Aguardando você".
  7. Clique em Enviar. Esperado: selo "Enviado". No Gmail, o e-mail aparece em Enviados, na mesma thread do original.
  8. Auditoria: `email_draft_created` e `email_sent` (com `message_id`). Teste também Descartar num segundo rascunho: `email_draft_discarded`.
  9. Se der 502 "insufficient authentication scopes", o escopo não entrou no token: repita os passos 1 e 3.
- [ ] **Gravar o vídeo (ticket 19, até 5 min) e entregar ao CPO.** Roteiro completo em `README.md`, seção "Roteiro do vídeo". Ordem:
  1. Login com a conta demo.
  2. Conversa simples: stream e badge de modelo e tokens.
  3. Imagem anexada.
  4. PDF anexado; pergunta de seguimento sobre o PDF.
  5. Tool web: linha "roteado para web_search" e URLs citadas.
  6. Compactação: limiar baixo (ex.: 2.000) em `/config`, escopo da Conversa; mandar mensagem (sem evento `compaction`, baixe para 500 e repita); recarregar para ver o marcador.
  7. Cap: em `/admin`, cap da conta demo em zero; mandar mensagem e mostrar o aviso. **Restaure o cap antes do passo 9.**
  8. `/auditoria` filtrada pela Conversa e `/creditos`.
  9. Share: abrir em janela anônima, revogar em `/compartilhados`, recarregar e mostrar o 404.
  10. MCP: `/mcp` com GitHub (`https://api.githubcopilot.com/mcp/` + PAT novo) ou o demo local `http://127.0.0.1:8765/mcp`; "quais meus repos".
  11. Google: `/conectores`, conectar, "qual meu último e-mail sobre X". Depende da validação do ticket 18 acima.
  Antes de gravar: `docker compose up -d --wait`, `cd api && uv run alembic upgrade head`, `cd web && npm run build`, `cd api && uv run uvicorn app.main:app --port 8000`. Se o deploy (16) sair antes, grave no link público.
- [ ] Ler `docs/ENTREVISTA.md`: 3 perguntas e resposta curta por ADR, mais o workflow com IA. As perguntas marcadas **Lacuna** são as mais prováveis de apertar.

- [x] **Decidir o fallback OpenAI (ADR 0012).** O ticket 19 achou que o ADR descreve um fallback para OpenAI que não existe no código: nada lê `OPENAI_API_KEY`. Ou implementa (ticket novo) ou escreve um ADR revisando o 0012. Está listado no README como limite conhecido. **Decidido (23/09): sem OpenAI, ADR 0018.**

- [x] **Duas decisões de `docs/LACUNAS.md` sem ticket.** (1) Reserva de crédito estimada localmente (~3 chars/token) em vez de `count_tokens`, contra o ADR 0004: emendar o ADR ou abrir ticket. (2) Turno cortado pelo teto de tool calls não é cobrado (06b): decidir se cobra. **Decidido (23/09): estimativa local fica (ADR 0019); turno cortado segue cobrado.**
- [x] **ADR 0010 vs código.** O ticket 18 usou httpx direto em vez da lib do Google que o ADR cita. Está em `DECISOES-AUTONOMAS.md`. Regra do repo: não contrariar ADR sem escrever outro. Decidir se emenda o 0010 ou aceita como está; você vai defender isso. **Decidido (23/09): libs oficiais de auth + PKCE, Gmail/Drive em httpx (ADR 0017, ticket 43).**
- [x] **Regra violada, para você saber:** o screenshot do ticket 21 (`21-tools-nao-admin.png`) saiu do Chromium do Playwright MCP, não do Brave. Os outros tickets da noite usaram Brave via playwright-core.

- [x] **Deploy (ticket 16): cadastros no GitHub e no Google.** App no ar em `/opt/tess-chat` no VPS. Runbook em `docs/INFRA.md`.
  1. Deploy key: GitHub > tess-chat > Settings > Deploy keys > Add. Título `vps`, read-only (sem "Allow write access"). Chave:
     `ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIIr2/U27AR9teYvHBLsIPw6wBiduSi/P30+uCAvPCaUi tess-chat-deploy@vps`
  2. No VPS, ligue o git: bloco "Ligar o git no VPS" de `docs/INFRA.md`. Sem isso o CI roda mas não puxa código novo.
  3. Secrets do Actions (Settings > Secrets and variables > Actions): `VPS_HOST=<omitido>`, `VPS_USER=<omitido>`, `VPS_SSH_KEY`.
  4. `VPS_SSH_KEY`, escolha: (a) conteúdo de `<omitido>`, a chave do trabalho, com sudo na produção; ou (b) recomendado: par só do CI, `ssh-keygen -t ed25519 -f tess-ci -N ""`, pública no fim de `~/.ssh/authorized_keys` do VPS, privada no secret. O agente não mexeu no `authorized_keys` do VPS compartilhado.
  5. Google Console > Credenciais > client OAuth > URIs de redirecionamento: adicione `https://chat.toneli.dev.br/api/connectors/google/callback`.
  6. Teste o CI: push na main (ou Actions > deploy > Run workflow) e confira `git -C /opt/tess-chat rev-parse HEAD`.
  7. TLS: o registro A `chat.toneli.dev.br` ainda não existia (NXDOMAIN no registro.br). Crie o registro A para `<omitido>`. Quando `dig +short chat.toneli.dev.br @8.8.8.8` devolver o IP, rode no VPS `sudo certbot --nginx -d chat.toneli.dev.br --non-interactive --agree-tos --redirect` e teste em janela anônima.
  8. Aceite "reiniciar o VPS mantém dados" NÃO foi testado com reboot: o VPS é produção do trabalho. Testado `down` + `up` sem `-v` (dados mantidos) e restart policy `unless-stopped` com docker `enabled`. Reboot real é decisão sua. **Adiado pelo Toneli em 23/09.**

- [x] **Produção: conectar Google e cadastrar o Stripe em https://chat.toneli.dev.br** (conectores e servidores MCP são por ambiente). Antes disso, no Google Console, confirmar que o redirect `https://chat.toneli.dev.br/api/connectors/google/callback` está cadastrado (o ticket 18 diz que sim).
- [ ] **Dica de demo do Stripe:** modelo da conta no padrão (3.8 Flash). Pedidos de ação funcionam numa frase ("gera o pagamento de R$ 1000 do celular"). Se quiser encurtar, desligue no popover de tools o `stripe_implementation_planner`, `search_stripe_documentation` e `send_stripe_feedback` da conversa.
- [ ] **Ticket 52: E2E real de MCP por OAuth (HITL).** Em https://chat.toneli.dev.br/mcp, clique no atalho Notion, autorize e volte. Peça no chat "lista minhas páginas do Notion". Repita com Stripe (modo teste): "lista meus clientes no Stripe". Local depende de o Notion aceitar redirect `http://localhost:8000` (**INFERIDO**). Cerca de 4 turnos de Gemini.
