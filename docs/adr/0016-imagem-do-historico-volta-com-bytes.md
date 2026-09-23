# ADR 0016 — Imagem de turno anterior volta ao modelo com os bytes

**Status:** aceito, 2026-09-23. Substitui a decisão 09b "turno anterior: todo arquivo vira `[anexo: nome]`" (`docs/DECISOES-AUTONOMAS.md`).

## Contexto
Produção, conversa `2d7bd6bf`, 23/09. O Toneli mandou um meme com um cachorro e um texto. No turno do anexo o Gemini respondeu certo. No turno seguinte (`E esse cachorro da imagem?`) disse "Bull Terrier branco". Depois inventou o texto da imagem. Causa: `sem_bytes` trocava toda imagem do histórico por `[anexo: image.png]`. O modelo não via a imagem e não sabia que não via.

Pesquisa (23/09): Anthropic, OpenAI e Gemini reenviam o histórico inteiro a cada request, com cache para baratear. LibreChat (`resendFiles` default `true`), Open WebUI, LobeChat e o template do Vercel reenviam toda imagem. LobeChat usa placeholder só em modelo sem visão, e o texto manda o modelo não descrever a imagem.

## Decisão
1. **Imagem própria de turno anterior volta com os bytes**, na resolução default: a mesma do turno do anexo. O prefixo do histórico fica igual entre turnos, então o cache implícito do Gemini pode cobrir. `anexos.partes_do_historico`.
2. **Todo outro arquivo vira `FORA_DO_CONTEXTO`**: `[anexo: nome — fora do contexto. Não descreva o conteúdo; peça ao usuário para reenviar.]`. Vale para PDF, imagem sumida do disco, data URI antiga e URL externa (SSRF).
3. **Mensagens antigas que vão para o Resumo não levam imagem** (`com_imagem=False`). O Resumo é texto; depois da Compactação, a imagem sai do contexto com o aviso do item 2.
4. **Reserva de crédito soma `TOKENS_IMAGEM` = 1120 por imagem** do histórico e da mensagem nova. O JSON das partes só tem a referência.

### Alternativas descartadas
- **`media_resolution` low no histórico (280 tokens).** Mais barato, mas o bug foi ler texto na imagem. Resolução baixa arrisca o mesmo erro, e a troca de resolução muda o prefixo e quebra o cache.
- **Teto das N últimas imagens.** Nenhuma fonte primária usa. A Compactação já corta histórico longo. YAGNI.
- **Tool `ver_anexo(id)`.** Depende do modelo decidir chamar. O modelo que errou não hesitou.
- **PDF também com bytes.** ~560 tokens por página, todo turno. O ADR 0015 já trata PDF do Drive por releitura via Tool.

## Consequências
- Cada imagem custa ~1120 tokens de entrada por turno até a Compactação (INFERIDO para `gemini-3.8-flash`; fonte: ai.google.dev/gemini-api/docs/media-resolution). O cache implícito pode cobrir parte. Não medido.
- Arquivo apagado do disco não quebra o turno: vira aviso.
- Pergunta de seguimento sobre PDF ainda depende da resposta anterior, mas o modelo agora sabe que não vê o arquivo.
