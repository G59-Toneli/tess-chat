import { useEffect, useState } from 'react'
import type { ChatStatus } from 'ai'
import { CircleDollarSignIcon } from 'lucide-react'
import { Link } from 'react-router'
import { PromptInputButton } from '@/components/ai-elements/prompt-input'
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
import { tokens } from '@/lib/contexto'
import { custoDaConversa, usd, type CustoConversa as Custo, type OrigemGasto } from '@/lib/painel'
import { cn } from '@/lib/utils'

const ORIGEM: Record<OrigemGasto, { rotulo: string; dica: string; cor: string }> = {
  resposta: { rotulo: 'Respostas', dica: 'O modelo respondendo você', cor: 'bg-chart-1' },
  compactacao: { rotulo: 'Resumo do histórico', dica: 'Compactação das mensagens antigas', cor: 'bg-chart-2' },
  roteador: { rotulo: 'Escolha de tool', dica: 'Roteador decidindo a tool', cor: 'bg-chart-3' },
  ligacao: { rotulo: 'Ligação', dica: 'Conversa por voz e tela', cor: 'bg-chart-4' },
}

/** Origem que o front ainda não conhece mostra o nome cru, sem quebrar. */
const origemDe = (o: string) => ORIGEM[o as OrigemGasto] ?? { rotulo: o, dica: o, cor: 'bg-muted-foreground' }

const pct = (parte: number, todo: number) =>
  `${(todo > 0 ? (parte / todo) * 100 : 0).toLocaleString('pt-BR', { maximumFractionDigits: 1 })} %`

/** Botão de custo da Conversa na barra do input: só ícone, o valor fica no modal (sem taxímetro na barra). Atualiza ao fim do turno e ao trocar de Conversa. Clique abre o detalhe. */
export function CustoConversa({ conversaId, status }: { conversaId?: string; status: ChatStatus }) {
  const [custo, setCusto] = useState<Custo | null>(null)
  const [erro, setErro] = useState(false)
  const ocioso = status === 'ready' || status === 'error'

  useEffect(() => {
    if (!conversaId) {
      setCusto(null)
      return
    }
    if (!ocioso) return
    let valido = true
    custoDaConversa(conversaId)
      .then((c) => {
        if (!valido) return
        setCusto(c)
        setErro(false)
      })
      .catch(() => valido && setErro(true))
    return () => {
      valido = false
    }
  }, [conversaId, ocioso])

  const total = custo?.total_micro_usd ?? 0
  const rotulo = erro ? 'Custo indisponível' : `Custo da conversa: ${usd(total)}`

  return (
    <Dialog>
      <DialogTrigger asChild>
        <PromptInputButton aria-label={rotulo} title="Custo da conversa" className={cn(erro && 'opacity-50')}>
          <CircleDollarSignIcon className="size-4" />
        </PromptInputButton>
      </DialogTrigger>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Custo desta conversa</DialogTitle>
          <DialogDescription>Soma de todas as chamadas a modelos feitas nesta conversa.</DialogDescription>
        </DialogHeader>
        {erro ? (
          <p className="text-sm text-muted-foreground">Não foi possível ler o custo. Tente de novo depois da próxima resposta.</p>
        ) : !custo || custo.chamadas === 0 ? (
          <p className="text-sm text-muted-foreground">Ainda não tem gasto nesta conversa. Mande uma mensagem para começar.</p>
        ) : (
          <Detalhe custo={custo} />
        )}
      </DialogContent>
    </Dialog>
  )
}

function Detalhe({ custo: c }: { custo: Custo }) {
  const { gasto_micro_usd: gasto, cap_micro_usd: cap, saldo_micro_usd: saldo } = c.saldo
  const largura = (parte: number) => `${cap > 0 ? Math.min((parte / cap) * 100, 100) : 0}%`
  const tiposToken: [string, number][] = [
    ['Entrada', c.input_tokens],
    ['Saída', c.output_tokens],
    ['Raciocínio', c.thinking_tokens],
    ['Cache', c.cache_read_tokens],
  ]
  return (
    <div className="space-y-5">
      <div>
        <p className="text-3xl font-semibold tabular-nums">{usd(c.total_micro_usd)}</p>
        <p className="text-sm text-muted-foreground">
          {c.chamadas} {c.chamadas === 1 ? 'chamada' : 'chamadas'} · média de {usd(Math.round(c.total_micro_usd / c.chamadas))} cada
        </p>
      </div>

      <section className="space-y-2.5" aria-label="Para onde foi">
        <h3 className="text-sm font-medium">Para onde foi</h3>
        <div className="flex h-2 gap-0.5 overflow-hidden rounded-full bg-muted">
          {c.por_origem.map((o) => (
            <div
              key={o.origem}
              className={origemDe(o.origem).cor}
              style={{ width: `${Math.max((o.custo_micro_usd / c.total_micro_usd) * 100, 1)}%` }}
            />
          ))}
        </div>
        <ul className="space-y-1.5">
          {c.por_origem.map((o) => (
            <li key={o.origem} className="flex items-center gap-2 text-sm">
              <span className={cn('size-2.5 shrink-0 rounded-sm', origemDe(o.origem).cor)} aria-hidden />
              <span className="min-w-0 flex-1 truncate" title={origemDe(o.origem).dica}>
                {origemDe(o.origem).rotulo}
                <span className="ml-1.5 text-xs text-muted-foreground">{o.chamadas}×</span>
              </span>
              <span className="text-xs text-muted-foreground tabular-nums">{pct(o.custo_micro_usd, c.total_micro_usd)}</span>
              <span className="w-24 text-right tabular-nums">{usd(o.custo_micro_usd)}</span>
            </li>
          ))}
        </ul>
      </section>

      <section className="space-y-2" aria-label="Tokens">
        <h3 className="text-sm font-medium">Tokens</h3>
        <dl className="grid grid-cols-4 gap-2">
          {tiposToken.map(([rotulo, n]) => (
            <div key={rotulo} className="rounded-md border bg-muted/30 px-2.5 py-2">
              <dt className="text-xs text-muted-foreground">{rotulo}</dt>
              <dd className="text-sm font-medium tabular-nums">{tokens(n)}</dd>
            </div>
          ))}
        </dl>
        <p className="text-xs text-muted-foreground">Raciocínio já está dentro da saída. Cache é entrada reaproveitada, mais barata.</p>
      </section>

      <section className="space-y-2 border-t pt-4" aria-label="Seu crédito">
        <div className="flex items-baseline justify-between text-sm">
          <span className="font-medium">Seu crédito</span>
          <span className="text-muted-foreground tabular-nums">
            {usd(gasto)} de {usd(cap)}
          </span>
        </div>
        <div className="flex h-1.5 overflow-hidden rounded-full bg-muted">
          <div className="bg-foreground/40" style={{ width: largura(gasto - c.total_micro_usd) }} />
          <div className="bg-foreground" style={{ width: largura(c.total_micro_usd) }} />
        </div>
        <p className="text-xs text-muted-foreground">
          Esta conversa é {pct(c.total_micro_usd, gasto)} do seu gasto. Saldo: {usd(Math.max(saldo, 0))}.
        </p>
        <Link to="/creditos" className="text-xs text-muted-foreground underline-offset-4 hover:underline">
          Ver créditos
        </Link>
      </section>
    </div>
  )
}
