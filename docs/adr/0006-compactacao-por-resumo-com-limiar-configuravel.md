# ADR 0006 — Compactação por Resumo, com limiar persistido em Configuração

**Status:** aceito, 2026-09-23

## Contexto
Gemini não compacta chat nativamente. Com janela de 1M, o avaliador nunca bate no limite real numa demo.

## Decisão
Hook `ProcessHistory` do Pydantic AI. Gatilho: tokens de entrada do último turno acima do limiar da Configuração da Conversa (default 100k, ajustável até bem baixo para a demo). Ação: os últimos N turnos ficam literais. O resto vira Resumo gerado pelo flash-lite com instrução do que preservar. Par tool-call e resultado nunca é separado. O Resumo é persistido. As Mensagens originais permanecem no banco e na UI. O chat não é interrompido: a compactação ocorre dentro do mesmo turno.

## Consequências
- Limiar baixo na demo faz o avaliador ver a compactação disparar e aparecer na auditoria.
- System prompt fixo no início preserva o cache implícito do Gemini.
