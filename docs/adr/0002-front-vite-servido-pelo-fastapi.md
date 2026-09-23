# ADR 0002 — Front React + Vite + shadcn + AI Elements, servido como estático pelo FastAPI

**Status:** aceito, 2026-09-23

## Contexto
Front é detalhe na vaga. A lógica avaliada está no backend. Dois deploys dobram a superfície a defender.

## Opções
1. Next.js separado, dois containers.
2. Vite + React buildado e servido pelo FastAPI, um container.
3. shadcn puro sem AI SDK, parser de stream manual.

## Decisão
Opção 2. `useChat` de `@ai-sdk/react` é lib npm, agnóstica de hospedagem, e fala o protocolo aberto de stream que o `VercelAIAdapter` emite. AI Elements são componentes shadcn. Não há nada da Vercel no deploy.

## Consequências
- Auth fica no Python (FastAPI-Users).
- Um Dockerfile multi-stage: build do front, cópia para o container do backend.
- Risco a validar no spike (ticket 01): AI Elements em Vite. Fallback: shadcn puro + `useChat`.
