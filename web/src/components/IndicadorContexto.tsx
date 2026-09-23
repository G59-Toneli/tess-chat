import { useEffect, useState } from 'react'
import type { ChatStatus } from 'ai'
import { PromptInputButton } from '@/components/ai-elements/prompt-input'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { faixa, fracao, lerContexto, resumo, type Contexto } from '@/lib/contexto'

const TAMANHO = 20
const CENTRO = TAMANHO / 2
const RAIO = 7.5
const TRACO = 2.5
const CIRCUNFERENCIA = 2 * Math.PI * RAIO

const COR = { normal: 'text-muted-foreground', alerta: 'text-amber-500', critico: 'text-destructive' }

/** Ponto no círculo de raio r, na fração f da volta, a partir do topo em sentido horário. */
function ponto(f: number, r: number) {
  const a = f * 2 * Math.PI - Math.PI / 2
  return { x: CENTRO + r * Math.cos(a), y: CENTRO + r * Math.sin(a) }
}

function Rosca({ contexto }: { contexto: Contexto | null }) {
  const f = contexto ? fracao(contexto) : 0
  const marca = contexto && contexto.limite > 0 ? contexto.limiar_compactacao / contexto.limite : null
  const [de, ate] = marca !== null && marca < 1 ? [ponto(marca, RAIO - 2.5), ponto(marca, RAIO + 2.5)] : [null, null]
  return (
    <svg width={TAMANHO} height={TAMANHO} viewBox={`0 0 ${TAMANHO} ${TAMANHO}`} aria-hidden className={COR[faixa(f)]}>
      <circle cx={CENTRO} cy={CENTRO} r={RAIO} fill="none" strokeWidth={TRACO} className="stroke-border" />
      {f > 0 && (
        <circle
          cx={CENTRO}
          cy={CENTRO}
          r={RAIO}
          fill="none"
          stroke="currentColor"
          strokeWidth={TRACO}
          strokeLinecap={f < 1 ? 'round' : 'butt'}
          strokeDasharray={`${Math.max(f * CIRCUNFERENCIA, 0.5)} ${CIRCUNFERENCIA}`}
          transform={`rotate(-90 ${CENTRO} ${CENTRO})`}
          className="transition-[stroke-dasharray] duration-500 ease-out motion-reduce:transition-none"
        />
      )}
      {de && ate && (
        <line x1={de.x} y1={de.y} x2={ate.x} y2={ate.y} strokeWidth={1} strokeLinecap="round" className="stroke-foreground/70" />
      )}
    </svg>
  )
}

/** Rosca na barra do input: quanto da janela de contexto o próximo turno carrega. Atualiza ao fim do turno e ao trocar de Conversa. */
export function IndicadorContexto({ conversaId, status }: { conversaId?: string; status: ChatStatus }) {
  const [contexto, setContexto] = useState<Contexto | null>(null)
  const [erro, setErro] = useState(false)
  const ocioso = status === 'ready' || status === 'error'

  useEffect(() => {
    if (!conversaId) {
      setContexto(null)
      return
    }
    if (!ocioso) return
    let valido = true
    lerContexto(conversaId)
      .then((c) => {
        if (!valido) return
        setContexto(c)
        setErro(false)
      })
      .catch(() => valido && setErro(true))
    return () => {
      valido = false
    }
  }, [conversaId, ocioso])

  const texto = erro
    ? 'Contexto indisponível. Tente de novo depois do próximo turno.'
    : !contexto || contexto.usado === 0
      ? 'Contexto vazio'
      : resumo(contexto)

  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <PromptInputButton aria-label={texto} className={cn(erro && 'opacity-50')}>
          <Rosca contexto={erro ? null : contexto} />
        </PromptInputButton>
      </TooltipTrigger>
      <TooltipContent side="top" className="max-w-sm">
        {texto}
      </TooltipContent>
    </Tooltip>
  )
}
