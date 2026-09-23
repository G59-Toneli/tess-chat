# 37 — Indicador de "trabalhando" entre tool calls

**Type:** task (AFK, só web/)
**Status:** resolved
**Blocked by:** nenhum
**Refs:** `docs/UI-GUIA.md`, https://www.beautifului.dev/ (referência visual obrigatória), skill `frontend-design:frontend-design`. Feedback do Toneli em 23/09 depois do teste do Stripe.

**Problema:** num turno com várias tools, quando um card fica "Concluída" não aparece nada até o próximo card surgir. Parece que o assistente terminou. O usuário não sabe se deve esperar.

**What to build:**
- Enquanto o stream do turno está aberto e não há texto nem tool em andamento no fim da mensagem, mostrar abaixo do último card um indicador de atividade: um componente animado do beautifului.dev (ex.: shimmer text, dots, pulse) com texto curto em pt-BR. O texto muda pelo contexto: antes da 1ª tool "Pensando…"; depois de uma tool concluída "Analisando o resultado…"; depois de 2+ tools pode manter "Trabalhando…". Opcional: tempo decorrido discreto ("12 s").
- Some quando chega texto do assistente, quando uma nova tool começa (o card dela já mostra "Rodando") e quando o stream fecha (inclusive com erro ou turno interrompido do ticket 30).
- Mesmo indicador no início do turno, antes do primeiro token (se hoje já existe algo, unificar).
- Respeitar `prefers-reduced-motion`. Dark e light.
- Sem mudança em `api/`: o estado vem do que o stream já entrega (status do useChat + partes da mensagem).

**Aceite:**
- [x] Screenshot dark `37-trabalhando-entre-tools.png` mostrando um card "Concluída" e o indicador abaixo, antes do próximo card. Pode usar stream simulado (API mockada) para congelar o estado.
- [x] Screenshot `37-trabalhando-inicio.png` antes do primeiro token.
- [x] O indicador não aparece em mensagens já concluídas ao recarregar.
- [x] `tsc` e `npm run build` limpos.

## Answer
- `components/Trabalhando.tsx`: reimplementa o Loading State do beautifului.dev (variante Dots, MIT) em CSS puro: grade 3x3 com frente em chevron, texto com shimmer e tempo decorrido. Keyframes no `index.css`, com `motion-safe`/`motion-reduce`.
- Aparece no início do turno (substitui o Pensando antigo) e no fim da última mensagem quando o fim é uma tool concluída: "Pensando…", "Analisando o resultado…" (1 tool), "Trabalhando…" (2+).
- Some com texto no fim, tool rodando, corte do ticket 30 e stream fechado (`status !== 'streaming'`, por isso não aparece ao recarregar). Checado no Brave contra API mockada que segura o stream.
- Ressalva: o tempo conta do zero a cada espera, não desde o início do turno.
- `REVISAR(human)`: `textoTrabalhando` (quando aparece e com qual texto).
