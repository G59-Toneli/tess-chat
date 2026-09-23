# 14 — Configurações por usuário e por conversa

**Type:** task (AFK)
**Status:** blocked
**Blocked by:** 12
**Refs:** `CONTEXT.md` (Configuração).

**What to build:** tabela `settings` (escopo usuário ou conversa): modelo, nível de thinking, limiar de compactação, limiar do Roteador, cap por usuário (admin). Herança: conversa sobrepõe usuário sobrepõe default. Tela de configurações. Evento `settings_changed` com diff.

**Aceite:**
- [ ] Baixar o limiar de compactação na UI e ver a compactação disparar na próxima mensagem.
- [ ] Trocar modelo para flash-lite e ver o modelo gravado na mensagem e no ledger.
