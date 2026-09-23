| ticket | início | fim | resultado | commit |
|---|---|---|---|---|
| 01 | 2026-09-22T21:54:17-03:00 | 2026-09-22T22:15:04-03:00 | PASSOU 9/9 (3 com ressalva: H3 setup radix, H6 flag, H7 só era moderna) | spike |
| 03 | 2026-09-22T22:18:47-03:00 | 2026-09-22T22:22:43-03:00 | PASSOU 6/6 pytest (compose + alembic do zero; REVOKE verificado por mutação) | feat(03) |
| 04 | 2026-09-22T22:24:00-03:00 | 2026-09-22T22:27:52-03:00 | PASSOU 8/8 pytest test_auth (register, login JWT, /users/me 401 sem token, 3 eventos) | feat(04) |
| 05 | 2026-09-22T22:28:40-03:00 | 2026-09-22T22:31:00-03:00 | PASSOU 7/7 pytest test_conversas (404 entre usuários, ordem, 2 eventos, cascade) | feat(05) |
| 06 | 2026-09-22T22:33:00-03:00 | 2026-09-22T22:55:00-03:00 | PASSOU 5/5 pytest test_chat (histórico do banco, tokens = usageMetadata gravado, 502 + llm_error); manual 2 turnos Gemini | feat(06) |
| 06 | (ver ticket) | (ver ticket) | aceite OK; arquivos entraram no commit 2c738a6 por colisão de stage | 2c738a6 |
| 07a | 2026-09-22T22:27:37-03:00 | 2026-09-22T22:42:32-03:00 | PASSOU: build sem erro de tipo; 5/5 pytest test_estaticos; docker build + run responde / (HTML) e /health; 10 rotas navegáveis no Playwright, dark 1440x900 | feat(07a) |
| 07a | 2026-09-22T22:45:40-03:00 | 2026-09-22T22:45:40-03:00 | PASSOU (rodada 2, UI-GUIA): +/compartilhados /perfil /admin, estados vazio/carregando/erro, login com cadastro e demo; 15 screenshots no Brave dark 1440x900; build limpo; docker ok | feat(07a) |
