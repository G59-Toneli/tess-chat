# 19 — README, vídeo e perguntas e respostas sobre as decisões

**Type:** task (HITL + AFK)
**Status:** resolved (parte AFK; vídeo no MANHA)
**Blocked by:** 17, 18

**AFK:** ler `docs/LACUNAS.md` e listar as lacunas no README como "limites conhecidos" e no guia como perguntas prováveis. README com arquitetura (diagrama), como rodar, decisões (links pros ADRs), limites conhecidos. `docs/ENTREVISTA.md`: para cada ADR, 3 perguntas prováveis e resposta curta. Roteiro do vídeo em ordem: login → conversa → imagem → PDF → tool web → compactação com limiar baixo → cap estourando → auditoria → share → MCP → Google.

**HITL:** Toneli grava o vídeo (≤ 5 min) e confirma recebimento/entrega à empresa.

**Aceite:**
- [x] Alguém sem contexto sobe o projeto local seguindo o README. (conferido: comandos e variáveis; não executado do zero)
- [x] `docs/ENTREVISTA.md` cobre os 11 ADRs (são 12; cobre os 12).

## Answer
`README.md` na raiz: arquitetura com dois Mermaid (componentes e turno), como rodar local, tabela dos 12 ADRs, limites conhecidos e roteiro do vídeo. `docs/ENTREVISTA.md`: 3 perguntas por ADR, marcando as lacunas, mais o workflow com IA. `.env.example` novo, com exceção no `.gitignore`.
Aceite 1 validado por conferência, não por execução: as chaves do `.env.example` batem com os campos de `Settings` e cada comando do README existe no repo. Ninguém subiu o projeto do zero seguindo o README.
Ressalvas: são 12 ADRs, não 11. O fallback OpenAI do ADR 0012 não está no código e entrou como limite. Deploy (16) e ticket 23 entram como pendentes. O ESTRUTURA.md ainda descreve MCP e Conector como inexistentes (retrato de antes do 17 e 18); não editei.
HITL: gravar o vídeo, roteiro no `MANHA.md`. Sem código, sem `REVISAR(human)`.
