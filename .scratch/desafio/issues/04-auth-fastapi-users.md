# 04 — Auth com FastAPI-Users

**Type:** task (AFK)
**Status:** resolved
**Blocked by:** 03
**Refs:** grilling Q9.

**What to build:** cadastro e login por e-mail e senha, JWT, tabela `users`. Seed de conta demo. Eventos `user_registered`, `login_ok`, `login_failed`.

**Aceite:**
- [x] Registrar, logar, acessar rota protegida com o token, ser recusado sem token.
- [x] Cada tentativa de login gera evento de auditoria.

## Answer
FastAPI-Users 15.0.5 com tabela `users` (migração 0002, GRANT para tess_app), JWT Bearer de 24 h, rotas `/auth/register`, `/auth/jwt/login`, `/users/me`.
Eventos `user_registered`, `login_ok` e `login_failed` (e-mail inexistente, senha errada, conta inativa); senha nunca vai ao payload.
Conta demo `demo@toneli.dev.br` semeada no lifespan, idempotente. 8 testes em `tests/test_auth.py` verdes.
Ressalva: `JWT_SECRET` e `DEMO_PASSWORD` têm default de dev; o deploy precisa definir no `.env`.
