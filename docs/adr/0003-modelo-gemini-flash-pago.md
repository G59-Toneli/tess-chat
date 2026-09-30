# ADR 0003 — gemini-3.8-flash no tier pago como modelo principal

**Status:** aceito, 2026-09-23

## Contexto
Chaves disponíveis: Gemini, Cohere, Jev, OpenAI opcional. Pesquisa em `research/02-modelos-gemini-jev.md`.

## Decisão
`gemini-3.8-flash`, tier pago. Motivos: stable, 1M de contexto, tool calling paralelo, PDF e imagem nativos, thinking configurável, US$ 0,75/3,75 por 1M. Demo de uma semana custa perto de US$ 7. O free tier usa o conteúdo para treino e não publica limites, inaceitável com PDFs de usuário. Pro custa ~3x sem ganho visível numa demo. Resumo de compactação usa `gemini-3.1-flash-lite`.

## Consequências
- Tabela de preço no banco com data de vigência (preço do Flash dobra em 2027-01-01).
- OpenAI só entra como fallback de provedor se o Gemini cair.
