import { useRef } from 'react'
import { isStaticToolUIPart, type ToolUIPart, type UIMessage } from 'ai'
import { ChevronDownIcon, CpuIcon, GlobeIcon, OctagonPauseIcon, RouteIcon, WrenchIcon } from 'lucide-react'
import { Shimmer } from '@/components/ai-elements/shimmer'
import { Source, Sources, SourcesContent, SourcesTrigger } from '@/components/ai-elements/sources'
import { getStatusBadge, Tool, ToolContent, ToolInput, ToolOutput } from '@/components/ai-elements/tool'
import { Badge } from '@/components/ui/badge'
import { CollapsibleTrigger } from '@/components/ui/collapsible'
import { ehRascunho, RascunhoEmail } from '@/components/RascunhoEmail'
import { fontesDaBusca, type DecisaoRoteador, type Uso } from '@/lib/tools'

// Bloco de tool call do stream (docs/UI-GUIA.md): nome, args, duração e resultado resumido.

const RESUMO_CHARS = 1200
// Sufixo que o Pydantic AI escreve para o modelo na 1ª falha. O card mostra só o motivo do servidor.
const PARA_O_MODELO = /\s*Fix the errors and try again\.\s*$/
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

// Tool MCP vem como <slug do servidor>_<4 hex>_<tool> (api/app/mcp.py, prefixo()).
const PREFIXO_MCP = /^([a-z][a-z0-9_]*?)_([0-9a-f]{4})_(.+)$/

/** Separa o servidor MCP do nome da tool. Tool nativa volta sem servidor. */
export function partesDoNome(nome: string): { servidor?: string; tool: string } {
  const m = PREFIXO_MCP.exec(nome)
  if (!m) return { tool: nome }
  const servidor = m[1].replace(/_/g, ' ')
  return { servidor: servidor.charAt(0).toUpperCase() + servidor.slice(1), tool: m[3] }
}

function segundos(ms: number) {
  return ms < 1000 ? `${Math.round(ms)} ms` : `${(ms / 1000).toFixed(1).replace('.', ',')} s`
}

export function LinhaRoteador({ decisao }: { decisao: DecisaoRoteador }) {
  return (
    <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
      <RouteIcon className="size-3.5" />
      Roteador {decisao.forcada ? 'escolheu' : 'sugeriu'} {decisao.tool} · confiança {decisao.confidence.toFixed(2).replace('.', ',')}
    </p>
  )
}

export function BlocoTool({
  parte,
  duracaoMs,
  interrompida = false,
  somenteLeitura = false,
}: {
  parte: ToolUIPart
  duracaoMs?: number
  interrompida?: boolean
  somenteLeitura?: boolean
}) {
  const nome = nomeDaTool(parte)
  const { servidor, tool } = partesDoNome(nome)
  // gmail_send vira cartão com Enviar/Descartar. Erro da tool (texto) segue no bloco comum.
  if (nome === 'gmail_send' && parte.state === 'output-available' && ehRascunho(parte.output))
    return <RascunhoEmail saida={parte.output} somenteLeitura={somenteLeitura} />
  const fontes = nome === 'web_search' ? fontesDaBusca(parte.output) : []
  const saida = typeof parte.output === 'string' && parte.output.length > RESUMO_CHARS
    ? `${parte.output.slice(0, RESUMO_CHARS)}…`
    : parte.output
  return (
    <div className="space-y-2">
      <Tool className="mb-0">
        {/* Header próprio: o nome encolhe com reticências; servidor, latência, estado e seta nunca se sobrepõem. */}
        <CollapsibleTrigger className="flex w-full min-w-0 items-center gap-2 p-3">
          <WrenchIcon className="size-4 shrink-0 text-muted-foreground" />
          {servidor && (
            <Badge variant="outline" className="max-w-32 truncate">
              {servidor}
            </Badge>
          )}
          <span className="min-w-0 truncate text-left text-sm font-medium" title={nome}>
            {tool}
          </span>
          <span className="ml-auto flex shrink-0 items-center gap-2">
            {duracaoMs !== undefined && !interrompida && (
              <span className="text-xs text-muted-foreground tabular-nums">{segundos(duracaoMs)}</span>
            )}
            {interrompida ? <BadgeInterrompida /> : getStatusBadge(parte.state)}
            <ChevronDownIcon className="size-4 text-muted-foreground transition-transform group-data-[state=open]:rotate-180" />
          </span>
        </CollapsibleTrigger>
        <ToolContent>
          <ToolInput input={parte.input} />
          {!interrompida && <ToolOutput output={saida} errorText={parte.errorText?.replace(PARA_O_MODELO, '')} />}
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

function BadgeInterrompida() {
  return (
    <Badge className="gap-1.5 rounded-full text-xs" variant="secondary">
      <OctagonPauseIcon className="size-4 text-amber-500" />
      Interrompida
    </Badge>
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
