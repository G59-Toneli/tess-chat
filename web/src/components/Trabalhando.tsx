import { useEffect, useState } from 'react'
import type { ChatStatus, UIMessage } from 'ai'
import { partesDeTool, toolRodando } from '@/components/BlocoTool'
import { cn } from '@/lib/utils'

// Indicador de "trabalhando" do turno (ticket 37). Reimplementa o Loading State do
// beautifului.dev (variante Dots, MIT) só com CSS: grade 3x3 com frente em chevron,
// texto com shimmer e tempo decorrido. Com reduced motion a grade fica parada e o tempo segue.

// Atraso de cada célula: coluna + distância da linha do meio. Forma um ">" que anda para a direita.
const ATRASOS = Array.from({ length: 9 }, (_, i) => ((i % 3) + Math.abs(Math.floor(i / 3) - 1)) * 90)

// Variante Orbit do mesmo Loading State, para a Compactação: células quadradas, centro apagado
// e um cometa que roda pela borda em sentido horário. Diferencia do chevron do "Pensando…".
const ORBITA = [0, 1, 2, 5, 8, 7, 6, 3]
const ATRASOS_ORBITA = Array.from({ length: 9 }, (_, i) => (ORBITA.includes(i) ? ORBITA.indexOf(i) * 110 : null))

// REVISAR(human): decide se o indicador aparece no fim da última mensagem e com qual texto.
// Aparece só com o stream aberto, sem tool rodando (o card e o Buscando já mostram), sem
// corte do ticket 30 e sem texto no fim (o próprio texto é o progresso). step-start e
// partes data-* não contam como fim: o adaptador manda step-start logo depois da tool.
// Reasoning não é renderizado, então com ele no fim o usuário ainda vê o vazio: mostra.
export function textoTrabalhando(m: UIMessage | undefined, status: ChatStatus): string | undefined {
  if (status !== 'streaming' || m?.role !== 'assistant' || toolRodando(m)) return undefined
  if (m.parts.some((p) => p.type === 'data-turno-interrompido')) return undefined
  const fim = m.parts.filter((p) => p.type !== 'step-start' && !p.type.startsWith('data-')).at(-1)
  if (fim?.type === 'text' && fim.text) return undefined
  const concluidas = partesDeTool(m).filter((p) => p.state === 'output-available' || p.state === 'output-error').length
  if (concluidas === 0) return 'Pensando…'
  return concluidas === 1 ? 'Analisando o resultado…' : 'Trabalhando…'
}

/** Segundos desde que o indicador montou. Cada espera conta do zero. */
function useDecorrido(): string {
  const [ds, setDs] = useState(0)
  useEffect(() => {
    const t = setInterval(() => setDs((d) => d + 1), 100)
    return () => clearInterval(t)
  }, [])
  const s = ds / 10
  const fmt = (n: number) => n.toFixed(1).replace('.', ',')
  return s < 60 ? `${fmt(s)} s` : `${Math.floor(s / 60)} min ${fmt(s % 60)} s`
}

export function Trabalhando({ texto, orbita = false }: { texto: string; orbita?: boolean }) {
  const decorrido = useDecorrido()
  return (
    <div role="status" aria-label={texto} className="flex w-fit items-center gap-2.5">
      <span aria-hidden className="grid shrink-0 grid-cols-[repeat(3,4px)] gap-[1.5px]">
        {(orbita ? ATRASOS_ORBITA : ATRASOS).map((atraso, i) =>
          atraso === null ? (
            <span key={i} className="size-1 rounded-[1px] bg-foreground opacity-[0.07]" />
          ) : (
            <span
              key={i}
              className={cn('size-1 bg-foreground opacity-15 motion-safe:animate-pixel-on', orbita ? 'rounded-[1px]' : 'rounded-full')}
              style={{ animationDelay: `${atraso}ms`, ...(orbita && { animationDuration: '950ms' }) }}
            />
          ),
        )}
      </span>
      <span className="bg-[linear-gradient(90deg,var(--muted-foreground)_35%,var(--foreground)_50%,var(--muted-foreground)_65%)] bg-size-[200%_100%] bg-clip-text text-sm font-medium text-transparent motion-safe:animate-shimmer-text motion-reduce:text-muted-foreground">
        {texto}
      </span>
      <span className="text-xs text-muted-foreground tabular-nums">{decorrido}</span>
    </div>
  )
}
