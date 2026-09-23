import { useEffect, useState } from 'react'
import type { ChatStatus } from 'ai'
import { PromptInputButton } from '@/components/ai-elements/prompt-input'
import { Link } from 'react-router'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { cn } from '@/lib/utils'
import { faixa, fracao, lerContexto, porcento, tokens, type Contexto } from '@/lib/contexto'

const TAMANHO = 20
const CENTRO = TAMANHO / 2
const RAIO = 7.5
const TRACO = 2.5
const CIRCUNFERENCIA = 2 * Math.PI * RAIO

const COR = { normal: 'text-muted-foreground', alerta: 'text-amber-500', critico: 'text-destructive' }
const BARRA = { normal: 'bg-foreground/60', alerta: 'bg-amber-500', critico: 'bg-destructive' }

function Rosca({ contexto }: { contexto: Contexto | null }) {
  const f = contexto ? fracao(contexto) : 0
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
    </svg>
  )
}

/** Rosca na barra do input: quanto falta para a Compactação, pelo contexto que o próximo turno carrega. Atualiza ao fim do turno e ao trocar de Conversa. */
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

  const vazio = !contexto || contexto.usado === 0
  const rotulo = erro ? 'Contexto indisponível' : vazio ? 'Contexto vazio' : `Contexto: ${porcento(contexto)} até resumir`

  return (
    <Popover>
      <PopoverTrigger asChild>
        <PromptInputButton aria-label={rotulo} className={cn(erro && 'opacity-50')}>
          <Rosca contexto={erro ? null : contexto} />
        </PromptInputButton>
      </PopoverTrigger>
      <PopoverContent side="top" align="start" className="w-72 gap-3 p-4" aria-label="Contexto">
        {erro ? (
          <p className="text-sm text-muted-foreground">Não foi possível ler o contexto. Tente de novo depois da próxima resposta.</p>
        ) : vazio ? (
          <p className="text-sm text-muted-foreground">Ainda não tem resposta nesta conversa.</p>
        ) : (
          <Detalhe contexto={contexto} conversaId={conversaId} />
        )}
      </PopoverContent>
    </Popover>
  )
}

function Detalhe({ contexto: c, conversaId }: { contexto: Contexto; conversaId?: string }) {
  const f = fracao(c)
  const passou = c.usado > c.limiar_compactacao
  return (
    <>
      <div className="flex items-baseline justify-between">
        <span className="text-sm font-semibold">Contexto</span>
        <span className={cn('text-sm font-medium tabular-nums', COR[faixa(f)])}>{porcento(c)}</span>
      </div>
      <div className="space-y-1.5">
        <div className="h-1.5 overflow-hidden rounded-full bg-muted">
          <div className={cn('h-full rounded-full', BARRA[faixa(f)])} style={{ width: `${Math.max(f * 100, 1)}%` }} />
        </div>
        <p className="text-xs text-muted-foreground tabular-nums">
          {tokens(c.usado)} de {tokens(c.limiar_compactacao)} tokens
        </p>
      </div>
      <p className="text-sm">
        {passou
          ? 'Passou do limite. As mensagens antigas vão ser resumidas.'
          : `Faltam ${tokens(c.limiar_compactacao - c.usado)} tokens para resumir as mensagens antigas.`}
      </p>
      <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1 border-t pt-3 text-xs">
        <dt className="text-muted-foreground">Modelo</dt>
        <dd className="truncate text-right font-mono">{c.modelo}</dd>
        <dt className="text-muted-foreground">Janela do modelo</dt>
        <dd className="text-right tabular-nums">{tokens(c.limite)} tokens</dd>
      </dl>
      <Link
        to={conversaId ? `/config?conversa=${conversaId}` : '/config'}
        className="text-xs text-muted-foreground underline-offset-4 hover:underline"
      >
        Mudar o limite
      </Link>
    </>
  )
}
