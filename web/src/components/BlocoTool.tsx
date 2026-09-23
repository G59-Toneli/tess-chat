import { useRef } from 'react'
import { isStaticToolUIPart, type ToolUIPart, type UIMessage } from 'ai'
import { CpuIcon, GlobeIcon, RouteIcon } from 'lucide-react'
import { Shimmer } from '@/components/ai-elements/shimmer'
import { Source, Sources, SourcesContent, SourcesTrigger } from '@/components/ai-elements/sources'
import { Tool, ToolContent, ToolHeader, ToolInput, ToolOutput } from '@/components/ai-elements/tool'
import { ehRascunho, RascunhoEmail } from '@/components/RascunhoEmail'
import { fontesDaBusca, type DecisaoRoteador, type Uso } from '@/lib/tools'

// Bloco de tool call do stream (docs/UI-GUIA.md): nome, args, duração e resultado resumido.

const RESUMO_CHARS = 1200
const RODANDO = new Set<ToolUIPart['state']>(['input-streaming', 'input-available'])

export const partesDeTool = (m: UIMessage) => m.parts.filter(isStaticToolUIPart) as ToolUIPart[]
export const nomeDaTool = (p: ToolUIPart) => p.type.slice('tool-'.length)
export const toolRodando = (m?: UIMessage) => !!m && partesDeTool(m).some((p) => RODANDO.has(p.state))

/** Duração medida no browser: do primeiro render com a tool pendente até o resultado. Histórico não tem. */
export function useDuracoes(mensagens: UIMessage[]): Map<string, number> {
  const inicio = useRef(new Map<string, number>())
  const duracao = useRef(new Map<string, number>())
  const agora = performance.now()
  for (const m of mensagens)
    for (const p of partesDeTool(m)) {
      if (RODANDO.has(p.state)) {
        if (!inicio.current.has(p.toolCallId)) inicio.current.set(p.toolCallId, agora)
      } else if (inicio.current.has(p.toolCallId) && !duracao.current.has(p.toolCallId)) {
        duracao.current.set(p.toolCallId, agora - inicio.current.get(p.toolCallId)!)
      }
    }
  return duracao.current
}

function segundos(ms: number) {
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1).replace('.', ',')} s`
}

export function LinhaRoteador({ decisao }: { decisao: DecisaoRoteador }) {
  return (
    <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
      <RouteIcon className="size-3.5" />
      Roteador escolheu {decisao.tool} · confiança {decisao.confidence.toFixed(2).replace('.', ',')}
    </p>
  )
}

export function BlocoTool({ parte, duracaoMs }: { parte: ToolUIPart; duracaoMs?: number }) {
  const nome = nomeDaTool(parte)
  // gmail_send vira cartão com Enviar/Descartar. Erro da tool (texto) segue no bloco comum.
  if (nome === 'gmail_send' && parte.state === 'output-available' && ehRascunho(parte.output))
    return <RascunhoEmail saida={parte.output} />
  const fontes = nome === 'web_search' ? fontesDaBusca(parte.output) : []
  const saida = typeof parte.output === 'string' && parte.output.length > RESUMO_CHARS
    ? `${parte.output.slice(0, RESUMO_CHARS)}…`
    : parte.output
  return (
    <div className="space-y-2">
      <Tool className="mb-0">
        <div className="relative">
          <ToolHeader type={parte.type} state={parte.state} title={nome} />
          {duracaoMs !== undefined && (
            <span className="pointer-events-none absolute top-1/2 right-10 -translate-y-1/2 text-xs text-muted-foreground tabular-nums">
              {segundos(duracaoMs)}
            </span>
          )}
        </div>
        <ToolContent>
          <ToolInput input={parte.input} />
          <ToolOutput output={saida} errorText={parte.errorText} />
        </ToolContent>
      </Tool>
      {fontes.length > 0 && (
        <Sources className="mb-0">
          <SourcesTrigger count={fontes.length}>
            <GlobeIcon className="size-3.5" />
            <span className="font-medium">{fontes.length} fontes consultadas</span>
          </SourcesTrigger>
          <SourcesContent>
            {fontes.map((f) => (
              <Source key={f.url} href={f.url} title={f.titulo} />
            ))}
          </SourcesContent>
        </Sources>
      )}
    </div>
  )
}

export function Buscando({ nome }: { nome: string }) {
  const texto = nome === 'web_search' ? 'Buscando na web…' : nome === 'web_fetch' ? 'Lendo a página…' : `Rodando ${nome}…`
  return (
    <div className="flex items-center gap-2 text-sm" role="status">
      <GlobeIcon className="size-4 animate-pulse text-muted-foreground" />
      <Shimmer as="span">{texto}</Shimmer>
    </div>
  )
}

export function BadgeUso({ uso }: { uso: Uso }) {
  const n = (x: number) => x.toLocaleString('pt-BR')
  return (
    <span className="flex items-center gap-1.5 text-xs text-muted-foreground" title="Modelo e tokens da resposta">
      <CpuIcon className="size-3.5" />
      {uso.modelo} · {n(uso.entrada)} entrada · {n(uso.saida)} saída
    </span>
  )
}
