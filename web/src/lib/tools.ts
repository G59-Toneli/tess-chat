// Tools (ADR 0009), decisões do Roteador (ADR 0005) e uso por Mensagem.
import { authHeader, ErroApi, type MensagemApi } from '@/lib/api'

export type ToolCatalogo = {
  nome: string
  origem: string
  descricao: string
  schema: Record<string, unknown>
  ativa_global: boolean
}
/** `servidor`: nome do Servidor MCP, só em origem mcp. */
export type ToolConversa = { nome: string; origem: string; descricao: string; ativa: boolean; servidor?: string | null }
export type DecisaoRoteador = { ts: string; tool: string; confidence: number; forcada: boolean }
/** A API já devolve estes campos em /messages; o tipo base do 07 não os declara. */
export type MensagemComUso = MensagemApi & {
  model: string | null
  input_tokens: number | null
  output_tokens: number | null
}
export type Uso = { modelo: string; entrada: number; saida: number; decisao?: DecisaoRoteador }

async function pedir<T>(caminho: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(caminho, { ...init, headers: { ...authHeader(), 'Content-Type': 'application/json' } })
  if (!r.ok) throw new ErroApi(r.status, (await r.json().catch(() => ({}))).detail)
  return (await r.json()) as T
}

export const listarCatalogo = () => pedir<ToolCatalogo[]>('/api/tools')
export const alternarGlobal = (nome: string, ativa: boolean) =>
  pedir<ToolCatalogo>(`/api/tools/${nome}`, { method: 'PUT', body: JSON.stringify({ ativa_global: ativa }) })
export const toolsDaConversa = (id: string) => pedir<ToolConversa[]>(`/api/conversations/${id}/tools`)
export const alternarNaConversa = (id: string, nome: string, ativa: boolean) =>
  pedir<ToolConversa[]>(`/api/conversations/${id}/tools`, { method: 'PUT', body: JSON.stringify({ [nome]: ativa }) })
export const decisoesDoRoteador = (id: string) => pedir<DecisaoRoteador[]>(`/api/conversations/${id}/roteador`)

// REVISAR(human): casa cada resposta do assistente com a decisão do Roteador do mesmo turno.
// A decisão é gravada antes do stream e as Mensagens do turno só no fim, todas com o mesmo
// created_at. Vale a última decisão com ts entre o turno anterior e este. Turno sem decisão
// (Jev fora) fica sem linha. Uso vem só na última linha do turno.
export function usoPorMensagem(linhas: MensagemComUso[], decisoes: DecisaoRoteador[]): Map<string, Uso> {
  const usos = new Map<string, Uso>()
  let anterior = 0
  let atual = 0
  for (const m of linhas) {
    if (m.role !== 'assistant') continue
    const fim = new Date(m.created_at).getTime()
    if (fim !== atual) [anterior, atual] = [atual, fim]
    const decisao = decisoes.filter((d) => {
      const t = new Date(d.ts).getTime()
      return t > anterior && t <= fim
    }).at(-1)
    if (m.model) usos.set(String(m.id), { modelo: m.model, entrada: m.input_tokens ?? 0, saida: m.output_tokens ?? 0, decisao })
  }
  return usos
}

/** O cap chega como 402 com detail "Cap de crédito atingido (...)". */
export function ehErroDeCap(e: Error & { statusCode?: number }): boolean {
  if (e.statusCode === 402) return true
  try {
    const detail = JSON.parse(e.message).detail
    return typeof detail === 'string' && detail.startsWith('Cap de crédito')
  } catch {
    return false
  }
}

/** Fontes do texto que web_search devolve: linhas "[i] título" seguidas de "URL: ...". */
export function fontesDaBusca(saida: unknown): { titulo: string; url: string }[] {
  if (typeof saida !== 'string') return []
  const fontes: { titulo: string; url: string }[] = []
  for (const bloco of saida.split(/\n\n(?=\[\d+\])/)) {
    const titulo = bloco.match(/^\[\d+\]\s*(.*)$/m)?.[1]?.trim()
    const url = bloco.match(/^URL:\s*(\S+)/m)?.[1]
    if (url) fontes.push({ titulo: titulo || url, url })
  }
  return fontes
}
