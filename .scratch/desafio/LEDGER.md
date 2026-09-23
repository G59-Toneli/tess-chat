| ticket | início | fim | resultado | commit |
|---|---|---|---|---|
| 01 | 2026-09-22T21:54:17-03:00 | 2026-09-22T22:15:04-03:00 | PASSOU 9/9 (3 com ressalva: H3 setup radix, H6 flag, H7 só era moderna) | spike |
| 03 | 2026-09-22T22:18:47-03:00 | 2026-09-22T22:22:43-03:00 | PASSOU 6/6 pytest (compose + alembic do zero; REVOKE verificado por mutação) | feat(03) |
| 04 | 2026-09-22T22:24:00-03:00 | 2026-09-22T22:27:52-03:00 | PASSOU 8/8 pytest test_auth (register, login JWT, /users/me 401 sem token, 3 eventos) | feat(04) |
| 05 | 2026-09-22T22:28:40-03:00 | 2026-09-22T22:31:00-03:00 | PASSOU 7/7 pytest test_conversas (404 entre usuários, ordem, 2 eventos, cascade) | feat(05) |
