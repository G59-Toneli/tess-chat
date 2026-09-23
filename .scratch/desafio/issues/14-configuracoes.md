# 14 — Configurações por usuário e por conversa

**Type:** task (AFK)
**Status:** resolved
**Blocked by:** 12
**Refs:** `CONTEXT.md` (Configuração).

**What to build:** tabela `settings` (escopo usuário ou conversa): modelo, nível de thinking, limiar de compactação, limiar do Roteador, cap por usuário (admin). Herança: conversa sobrepõe usuário sobrepõe default. Tela de configurações. Evento `settings_changed` com diff.

**Aceite:**
- [x] Baixar o limiar de compactação na UI e ver a compactação disparar na próxima mensagem.
- [x] Trocar modelo para flash-lite e ver o modelo gravado na mensagem e no ledger.

**Adendo (do 07b):** `PUT /api/tools/{nome}` (toggle global) deve exigir `current_superuser` do ticket 15. Uma linha.

## Answer
Tabela `settings` (migração 0011), uma linha por escopo; herança Conversa > Usuário > `.env`, campo a campo, resolvida por dependência do chat (`app/configuracao.py`). O chat lê modelo, nível de raciocínio, limiar de compactação e limiar do Roteador da Configuração do turno. `settings_changed` leva o diff. Cap por Usuário grava em `caps` via `PUT /api/admin/usuarios/{id}/cap` (só admin). Toggle global de Tool agora exige `current_superuser`.
Tela `/config` com seletor de escopo (conta ou Conversa), herança visível e tema; cap editado em `/admin`. Aceites provados com FunctionModel em `tests/test_configuracao.py`; 2 chamadas reais ao flash-lite para validar o nível de raciocínio.
Ressalva: `test_roteador::test_anexo_vai_no_state` já falhava antes (URL `data:` recusada desde o 09).
REVISAR(human): `resolver` em `app/configuracao.py`.
