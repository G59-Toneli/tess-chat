# 77 — Falas da Ligação no histórico e histórico na Ligação

**Type:** task (api/ + web/)
**Status:** resolved
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

### 1. Um par por troca, não um bloco único
- **Conceito:** no fim da Ligação, cada troca vira duas Mensagens: o que o usuário disse e o que o agente respondeu. Falas seguidas do usuário se juntam numa Mensagem só.
- **Por quê:** o chat, a Compactação e o histórico do Gemini contam turnos por Mensagem de usuário (`ponto_de_corte`, `compactacao_turnos_literais`). Um bloco único com a Ligação inteira seria 1 turno gigante: a Compactação não teria onde cortar e a tela mostraria uma parede de texto. Com pares, a Ligação é igual a uma conversa digitada e o resto do sistema não sabe a diferença.
- **Onde:** `api/app/voz.py:_trocas`, `api/app/voz.py:gravar_falas`.
- **Pergunta de revisão:** "Por que gravar um par por troca e não a transcrição inteira numa Mensagem?"
  **Resposta:** Porque tudo que já existe conta turno por Mensagem: Compactação, corte de histórico, tela. Um bloco só quebraria a Compactação e viraria uma parede de texto. Com pares, a Ligação continua a Conversa sem código novo nos outros módulos.

### 2. Marca de Ligação como parte `data-ligacao`
- **Conceito:** a Mensagem guarda uma parte extra `{"type": "data-ligacao"}`. O front procura essa parte e mostra "por voz". O modelo de texto ignora partes `data-*`.
- **Por quê:** o `data-turno-interrompido` do ticket 30 já faz isso, então segue o padrão. Coluna nova em `messages` exigiria migração e mexeria no formato que o chat lê e grava. A parte viaja com a Mensagem, inclusive no link compartilhado.
- **Onde:** `api/app/voz.py:_mensagem`, `web/src/pages/Chat.tsx` (`porVoz`).
- **Pergunta de revisão:** "Como o front sabe que uma Mensagem veio da voz?"
  **Resposta:** A API grava uma parte `data-ligacao` junto do texto. O front acha essa parte e mostra o indicador. Não precisei de migração, e o modelo de texto ignora a parte.

### 3. Histórico entra como texto na instrução, cortado do mais novo para o mais antigo
- **Conceito:** ao abrir a Ligação, as últimas Mensagens de usuário e assistente viram texto ("Usuário: ...", "Assistente: ...") dentro da instrução do sistema. Imagem, PDF e tool ficam fora. O teto é 4000 tokens (`ligacao_historico_tokens`), estimados em 3 caracteres por token.
- **Por quê:** o Gemini Live recebe a instrução na abertura e o contexto de voz custa mais que o de texto (áudio e imagem em cada turno). Cortar pelo mais antigo mantém o que o usuário acabou de falar. A Mensagem que estoura o teto sai inteira: meia frase confunde o modelo. Alternativa que caiu: mandar o histórico como turnos `send_client_content`, que precisa de outro caminho no seam do Gemini.
- **Onde:** `api/app/voz.py:historico_em_texto`, `api/app/voz.py:_instrucao`.
- **Pergunta de revisão:** "Como a Ligação sabe o que foi dito antes no chat?"
  **Resposta:** No início eu monto um texto com as últimas Mensagens, só texto, e mando na instrução do Gemini. Corto do mais antigo para caber em 4000 tokens. Imagem e PDF não vão, porque custam caro no Live e a voz não precisa deles.

## Answer
Falas viram Mensagens no fim único (`_encerrar`, `gravar_falas`): um par usuário/assistente por troca, com a parte `data-ligacao`; vazio não entra; fala aberta do agente entra como veio; `voice_call_ended` ganhou `mensagens` no payload. A Ligação abre com o histórico em texto na instrução (teto `ligacao_historico_tokens`, 4000). Front: indicador "por voz" na Mensagem e a Conversa remonta com o histórico recarregado ao fechar o painel. Sem migração. `test_voz.py`: 15 passam (5 novos, incluindo um turno de texto depois da Ligação que vê as falas). `npm run build` limpo; `checar-responsivo` /c/:id sem violação; screenshots `77-conversa-por-voz-1440.png` e `-390.png`.
Ressalvas: a recarga ao desligar não foi vista em E2E (sem Gemini real; o 80 cobre); o screenshot usa Mensagens semeadas no banco. `REVISAR(human)`: `historico_em_texto`, `_trocas` (junto de `gravar_falas`).
