# 81 — ESTUDO-VOZ consolidado e roteiro dos dois vídeos

**Type:** docs
**Status:** ready-for-agent
**Blocked by:** 80 (pode começar depois do 76 e 78 e fechar depois do 80)
**Refs:** "Paradas de estudo" dos tickets 75 a 80. ADR 0026 a 0028. `docs/ENTREVISTA.md`, `docs/ESTRUTURA.md`, `docs/MOTIVACOES.md`.

**Objetivo:** o Toneli estuda a Ligação de ponta a ponta num arquivo só e grava os vídeos por roteiro.

## Escopo
1. **`docs/ESTUDO-VOZ.md`**, em ordem de leitura (do clique no botão até o débito no Ledger). Cada parada tem:
   - **Conceito:** o que é, em 2 ou 3 frases simples.
   - **Por quê:** a escolha e a alternativa que caiu.
   - **Onde:** `arquivo:linha`.
   - **Pergunta de entrevista** + resposta curta que o Toneli consegue falar.
   Juntar as paradas dos tickets 75 a 80. Conferir cada `arquivo:linha` no código atual. Incluir um diagrama de sequência em texto (browser, backend, Gemini).
2. **`docs/ROTEIRO-VIDEOS.md`:**
   - **Vídeo 1, demo (3 a 4 min):** compartilhar a aba de um PR do tess-chat e perguntar "o que esse diff faz?"; trocar para uma aba com gráfico ou dashboard e perguntar sobre ele; desligar e mostrar as falas no histórico e a Ligação em `/auditoria` e `/creditos`.
   - **Vídeo 2, arquitetura (8 a 10 min):** o diagrama; proxy vs token efêmero; ticket; a Ligação como turno longo; crédito (reserva, acerto, preço de tabela); 1 fps; por que sem Jev e sem tools; limites assumidos (9 min, sem resumption, um processo) e próximos passos.
   Falas curtas, em tópicos, para ler sem decorar.
3. `docs/ESTRUTURA.md` e `docs/MOTIVACOES.md` com a Ligação. `README.md`: uma seção curta da Ligação.

## Aceite
- Todo `arquivo:linha` do ESTUDO confere com o código.
- Chamadas reais: 0.
