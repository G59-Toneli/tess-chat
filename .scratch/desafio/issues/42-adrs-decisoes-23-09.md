# 42 — ADRs das decisões do Toneli em 23/09 (fallback, reserva, turno cortado)

**Type:** task (AFK, só docs)
**Status:** resolved
**Blocked by:** nenhum
**Refs:** ADR 0012, ADR 0004, `docs/LACUNAS.md`, `README.md` (limites conhecidos), `docs/ENTREVISTA.md`, `MANHA.md`.

**Decisões (Toneli, 23/09):**
1. Sem fallback OpenAI: não há chave. Fica retry com backoff (tenacity, `api/app/resiliencia.py`) e a cadeia `gemini-3.8-flash` → `gemini-3.7-flash`.
2. Reserva de crédito segue com estimativa local ~3 chars/token (`api/app/chat.py`, `_estimar_input`). Motivo: a reserva só segura crédito; a cobrança final usa o `usage` real (ADR 0004). `count_tokens` custaria uma ida de rede por turno antes do primeiro token e mais um ponto de falha, cujo fallback seria a própria estimativa.
3. Turno cortado pelo teto de tool calls continua não cobrado.
4. Teste de reboot do VPS adiado (produção do trabalho).

**What to build:**
- ADR 0018 revisando o 0012 (decisão 1). Status do 0012 aponta para o 0018.
- ADR 0019 revisando o 0004 na parte da reserva (decisão 2). Status do 0004 aponta para o 0019.
- `docs/LACUNAS.md`: fechar as duas decisões pendentes (2 e 3) citando o Toneli e a data; registrar o reboot como adiado.
- `README.md`: o limite do fallback OpenAI vira referência ao ADR 0018.
- `docs/ENTREVISTA.md`: pergunta + resposta curta para 0017 (conector Google com libs oficiais de auth; ticket 41 escreve o ADR em paralelo, cite pelo número e pela decisão do ticket 41), 0018 e 0019.
- Não tocar em `api/`, `web/` nem em `docs/adr/0017*`.

**Aceite:**
- [ ] ADRs 0018 e 0019 escritos no formato dos existentes.
- [ ] LACUNAS, README e ENTREVISTA atualizados.
- [ ] Chamadas reais: nenhuma.

## Answer
- ADR 0018 (sem fallback OpenAI) e ADR 0019 (reserva por estimativa local) escritos; status do 0012 e do 0004 apontam para eles.
- LACUNAS: reserva e OpenAI fechados citando Toneli 23/09; reboot do VPS registrado como adiado. README e ENTREVISTA (0017, 0018, 0019) atualizados.
- Divergência: a decisão 3 diz "não cobrado", mas o código cobra o turno cortado desde o ticket 30 (`on_cancel` em `chat.py`). Docs alinhados ao código. Se o Toneli quer não cobrar, é mudança em `api/`, fora deste ticket.
- Ressalva: comentário em `api/app/chat.py:56` ainda cita o fallback OpenAI do ADR 0012; fora do escopo (api/).
- Sem REVISAR(human). Nenhuma chamada real.
