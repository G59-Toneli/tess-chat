# Para o Toneli de manhã

Itens que precisam de você. O orquestrador acrescenta aqui durante a noite.

- [ ] **Trocar o `GITHUB_PAT`.** Vazou em texto aberto no log local da sessão do agente do ticket 03. Não foi para o repo. Gere um novo, atualize o `.env`.
- [x] `TAVILY_API_KEY` adicionada (free, 1.000 créditos/mês). Testes do ticket 10 usam resposta gravada, não a API.
- [ ] Ler `docs/DECISOES-AUTONOMAS.md`: decisões que os agentes tomaram sozinhos. Já tem a do JWT_SECRET e DEMO_PASSWORD com default de dev.
- [ ] Ler os `REVISAR(human)` no código: `grep -rn "REVISAR(human)" api/`. São as funções que você ia escrever e que caem na entrevista.
- [ ] Pegar chaves SSH do VPS do trabalho (usuário, IP, arquivo .pem) e salvar em `~/.ssh/`. Me passar o caminho. Criar registro A `chat.toneli.dev.br` apontando pro IP desse VPS.
- [ ] Criar projeto OAuth no Google seguindo `docs/WIZARD-GOOGLE.md` (quando existir). Cadastrar seu e-mail e o do CPO como test users.
