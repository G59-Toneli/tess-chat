# Roteiro dos dois vídeos da Ligação

Falas curtas, em tópicos. Lê, não decora. O estudo do mecanismo está em `docs/ESTUDO-VOZ.md`; o número da parada vai entre colchetes.

## Antes de gravar

- **Brave**, nunca Chrome. Tema dark. Uma janela só, sem notificações.
- **Custo:** cada Ligação de 1 min custa ~US$ 0,006 a preço de tabela e R$ 0 na chave free. Ensaio conta como chamada real. Ensaia sem Ligação (só a tela e o texto) e faz no máximo 2 Ligações reais por vídeo, de até 2 min. Confirma o teto da etapa no LEDGER antes.
- **Privacidade:** a chave free deixa o Google treinar com voz e tela. Não abre e-mail, token, `.env` nem PR privado com dado de cliente.
- **Produção:** `https://chat.toneli.dev.br`, conta demo. Confere que o Cap da conta demo tem saldo (a reserva de uma Ligação é US$ 0,345).
- **Abas prontas:** (1) o tess-chat numa Conversa nova. (2) Um PR do tess-chat com diff pequeno e legível, no GitHub. (3) `/creditos` do próprio app, que tem o gráfico de gasto por dia. (4) `/auditoria`.
- **Microfone e fone.** Fone evita eco. Testa o microfone antes.
- **Se a Ligação não abrir:** o erro no painel diz o motivo (402 Cap, 409 já em ligação, 429 teto). Ver `docs/PROTOCOLO-LIGACAO.md`.

---

## Vídeo 1: demo (3 a 4 min)

Objetivo: mostrar que o agente ouve, vê a tela e que tudo fica auditado e cobrado.

### 0:00 a 0:25. Abertura
- "Oi, sou o Toneli. Este é o tess-chat. Vou mostrar a Ligação: voz com o agente e compartilhamento de tela."
- Mostra a Conversa. Aponta o botão de telefone no topo do chat.

### 0:25 a 1:45. Cena 1: o que esse diff faz?
- Clica em **Ligar**. O painel mostra "conectando" e depois "em ligação". O contador começa.
- Clica em **Compartilhar tela**. Escolhe a **aba do PR**. Mostra a prévia pequena da tela no painel.
- Fala: "O que esse diff faz?"
- Deixa o agente responder inteiro. Aponta a transcrição ao vivo.
- Fala: "E o arquivo de teste, o que ele cobre?" Mostra que ele segue a conversa.
- Se der: interrompe o agente falando por cima uma vez. Mostra que ele para na hora [13].

### 1:45 a 2:45. Cena 2: gráfico ou dashboard
- **Troca o compartilhamento** para a aba `/creditos` (gráfico de gasto por dia). Barra do browser: parar e compartilhar de novo, ou compartilhar a janela inteira e trocar de aba.
- Fala: "O que esse gráfico mostra? Qual dia gastou mais?"
- Mostra que a resposta vem do que está na tela agora, com até 1 s de atraso [11].

### 2:45 a 3:30. Cena 3: desligar e provar
- Clica em **Desligar**. O painel fecha e o histórico recarrega.
- Mostra as **falas na Conversa**, com o indicador "por voz" [15].
- Abre `/auditoria`, filtra pela Conversa. Mostra `voice_call_started`, `screen_share_started`, `screen_share_stopped`, `voice_call_ended`. No `voice_call_ended`: duração, motivo `desligou`, tokens por modalidade, custo [19].
- Abre o custo da Conversa: origem **Ligação** [20]. Abre `/creditos`: a linha do `gemini-3.8-live` no Ledger, preço de tabela [18].

### 3:30 a 3:50. Fecho
- "Tudo passa pelo servidor: o crédito e a auditoria não dependem do browser. No próximo vídeo eu explico como."

**Se o modelo disser que não vê a tela:** para de compartilhar, compartilha de novo e repete a pergunta. Aconteceu no spike com a instrução antiga [12].

---

## Vídeo 2: arquitetura (8 a 10 min)

Objetivo: o avaliador sai sabendo o que trafega em cada ponto e por que cada escolha foi feita. Tela: o diagrama de sequência de `docs/ESTUDO-VOZ.md`, o `voz.py` aberto, e o painel de auditoria quando citar evento.

### 0:00 a 0:40. O que é
- "A Ligação é uma conversa por voz em tempo real dentro de uma Conversa, com a tela como contexto."
- "Três atores: o browser, o servidor FastAPI e o Gemini Live. O servidor está no meio."
- "Sem tools e sem Jev: o agente só conversa e olha."

### 0:40 a 2:40. O diagrama [visão geral]
- Mostra o diagrama de sequência. Lê em 5 passos:
  1. **Clique.** O browser pega o microfone. Só depois pede o Ticket [1].
  2. **Ticket.** `POST /api/voz/ticket`, com Bearer. O servidor confere vaga e Cap. Devolve um código de 30 s [3].
  3. **Conexão.** WebSocket com `?ticket=`. O servidor consome o ticket, ocupa a vaga, confere o Cap de novo, abre o Gemini [5].
  4. **Conversa.** Áudio sobe em binário, 1024 bytes a cada 32 ms. Frame sobe em JSON, 1 por segundo. Áudio e transcrição descem [9, 10].
  5. **Fim.** Um caminho só: grava falas, acerta o crédito, audita, libera a vaga [19].
- "Nos dois sentidos, cada byte passa pelo servidor."

### 2:40 a 4:10. Proxy vs token efêmero
- "Eu podia dar ao browser um token efêmero e ele falava direto com o Gemini. Menos código, um salto a menos."
- "Só que aí o servidor fica cego. O `usage_metadata` chegaria ao browser, e o Cap e a auditoria dependeriam do que o browser reporta. O browser pode mentir."
- "Cap e auditoria são obrigatórios. Então: proxy."
- "Preço: um salto a mais. Dezenas de ms contra centenas do modelo. INFERIDO, não medi o salto sozinho."
- Alternativas que caíram, uma frase cada: SSE só vai em um sentido; WebRTC pede servidor de mídia e o Gemini fala WebSocket; cascata STT → LLM → TTS tem latência pior e o reconhecimento do browser não funciona no Brave [6].

### 4:10 a 4:50. Ticket
- "O browser não manda header no WebSocket. Um JWT na URL ficaria 24 h no log do nginx."
- "O ticket é uso único e vale 30 s. O servidor faz `pop` antes de checar a validade. Vazou no log, já está gasto."
- Mostra `_consumir` em `voz.py` [3]. Cita o 4401 como prova de que o upgrade passa no nginx [4].

### 4:50 a 5:30. A Ligação como turno longo
- "A Ligação reserva a vaga de turno da Conversa, a mesma do chat de texto."
- "Texto durante a Ligação recebe 409. Sem lock novo."
- "Uma Ligação por Usuário, teto global de 3. Tudo em memória, um processo [7]."
- "Duas tasks fazem o relay, uma por sentido. Quando uma acaba, a outra é cancelada e esperada [8]."

### 5:30 a 7:10. Crédito: reserva, acerto e preço de tabela
- **Reserva.** "No ticket e na conexão, eu calculo o custo máximo de 9 min: 25 tokens por segundo de áudio nos dois sentidos e um Frame por segundo. A preço de tabela dá US$ 0,345. Só abre se cabe no Cap do Usuário e no global [17]."
- "Ressalva que eu falo sozinho: a reserva é uma checagem, não bloqueia saldo. Nada é gravado até o fim."
- **Acerto.** "No fim, o servidor soma o `usage_metadata` de todos os turnos, cada modalidade no seu preço: áudio, imagem, texto e pensamento. Grava uma linha no Ledger [18]."
- "Se a Ligação cai antes do primeiro turno completo, estima por duração e marca `estimado`."
- **Preço de tabela.** "A chave é free e custa zero. Se o Cap contasse o real, nunca dispararia. Então cobro o preço do modelo pago. O Crédito mede quanto custaria."
- Mostra o `voice_call_ended` na auditoria com tokens por modalidade.

### 7:10 a 8:00. 1 fps
- "A tela vai como Frame: JPEG, um por segundo, lado maior 1280. O modelo lê imagem, não assiste vídeo. A API não aceita mais de 1 por segundo [11]."
- "Medi antes de decidir: 264 tokens por Frame a 1280 e a 768. O custo não depende da resolução. Fiquei em 1280."
- "Limite: movimento rápido fica fora. O agente vê a tela de até 1 s atrás."

### 8:00 a 8:40. Por que sem Jev e sem tools
- "O Jev força a tool no passo 1 de um turno de requisição e resposta. A Ligação é fluxo contínuo. Um roteador na frente atrasa a fala [16]."
- "Sem tools, o agente só conversa e olha a tela. É um limite assumido."

### 8:40 a 9:40. Limites assumidos e próximos passos
- **Limites:** 9 minutos. Sem session resumption. Um processo só: restart derruba a Ligação. Reserva não segura saldo. Free tier treina com o conteúdo.
- **Próximos passos, em ordem:** session resumption; reserva gravada no Ledger; medir a latência com mais perguntas por sessão e testar `thinking_budget`; mover a sessão para fora do processo [23].
- Fecho: "Está tudo nos ADRs 0026 a 0028 e em `docs/ESTUDO-VOZ.md`."

---

## Três perguntas difíceis do avaliador (vídeo 2, depois do fecho)

### 1. "Você pôs um proxy no meio. Isso não soma latência e um ponto de falha?"
**Resposta curta:** "Soma um salto, dezenas de ms contra centenas do modelo. Não medi o salto sozinho, é INFERIDO. Aceitei porque no proxy eu vejo o uso real do Gemini, e o Cap e a auditoria são obrigatórios. O ponto de falha extra é o servidor, e todo fim, inclusive queda, passa por um caminho só que acerta o crédito e libera a vaga."

### 2. "Sua reserva de 9 minutos não segura nada. Então o Cap não vale durante a chamada."
**Resposta curta:** "Certo. Ela só confere que o gasto de agora mais US$ 0,345 cabe no Cap, no ticket e na conexão. Não grava nem bloqueia saldo. Duas chamadas simultâneas podem passar juntas, e 0,345 não é teto real, porque cada turno cobra o contexto de novo (INFERIDO). Com uma Ligação por Usuário, o risco é pequeno. O próximo passo é gravar uma linha de reserva no Ledger e ajustar no acerto."

### 3. "Um segundo e meio de espera para uma voz é lento. Por que o seu passa de 2 s?"
**Resposta curta:** "Medi por salto, no browser, da minha rede residencial até o VPS. A rede soma menos de 50 ms. Com o servidor local a mesma medição dá 1,7 s, então não é o VPS. O tempo está dentro do Gemini: cerca de 1,3 s esperando ter certeza de que parei de falar, e de 0,4 a 3 s do modelo pensando. Reduzi a espera em 400 ms com a config do VAD e o total não caiu, porque o pensamento variou mais. O `thinking_level` não existe nesse modelo Live. Os 0,5 s que apareceram antes vinham de um script sem browser, outra régua."

## Depois de gravar

- Confere no `/auditoria` que as Ligações do vídeo aparecem, e registra as chamadas reais gastas no LEDGER.
- Grava o vídeo 1 antes do 2. O vídeo 2 usa os eventos do vídeo 1 como exemplo.
