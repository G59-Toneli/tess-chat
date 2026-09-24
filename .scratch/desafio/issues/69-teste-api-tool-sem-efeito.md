# 69 — Teste de tool por API não repete POST real

**Type:** bug (api/, web/)
**Status:** open
**Refs:** `api/app/api_tools.py` (`cadastrar`, `testar`), `web/src/pages/ApiTools.tsx` (`Formulario`), revisão de 24/09.

**Problema:** o botão Testar faz o request real, e o `cadastrar` do back testa de novo. Uma tool POST com efeito (criar pedido, cobrança) roda duas vezes só para ser cadastrada, sem aviso.

## Escopo
1. Não repetir o request no cadastro quando o teste do mesmo body já passou, ou avisar na tela antes de testar POST. Escolher, registrar em DECISOES-AUTONOMAS.

## Aceite
- Cadastrar uma tool POST faz no máximo um request real.
