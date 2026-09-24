// Auditoria, Crédito e admin (ticket 15). Valores em micro-USD inteiro (ADR 0004).
import { api } from '@/lib/api'

export type Evento = {
  id: number
  ts: string
  user_id: string | null
  user_email: string | null
  conversation_id: string | null
  event_type: string
  payload: Record<string, unknown>
  input_tokens: number | null
  output_tokens: number | null
  cost_micro_usd: number | null
  latency_ms: number | null
  model: string | null
}
export type PaginaEventos = { items: Evento[]; total: number; limit: number; offset: number }
export type FiltroAuditoria = {
  user_id?: string
  conversation_id?: string
  event_type?: string
  desde?: string
  ate?: string
  limit: number
  offset: number
}

export type Saldo = { gasto_micro_usd: number; cap_micro_usd: number; saldo_micro_usd: number }
export type LinhaLedger = {
  id: number
  ts: string
  user_id: string
  conversation_id: string | null
  model: string
  input_tokens: number
  output_tokens: number
  thinking_tokens: number
  cache_read_tokens: number
  cost_micro_usd: number
}
export type Painel = {
  saldo: Saldo
  por_dia: { dia: string; custo_micro_usd: number }[]
  por_modelo: { model: string; custo_micro_usd: number; chamadas: number }[]
  ultimas: LinhaLedger[]
}
export type UsuarioAdmin = { id: string; email: string; is_superuser: boolean; gasto_micro_usd: number; cap_micro_usd: number }

const fuso = () => Intl.DateTimeFormat().resolvedOptions().timeZone

export function listarEventos(f: FiltroAuditoria) {
  const q = new URLSearchParams()
  for (const [k, v] of Object.entries(f)) if (v !== undefined && v !== '') q.set(k, String(v))
  return api<PaginaEventos>(`/api/audit?${q}`)
}
export const tiposDeEvento = () => api<string[]>('/api/audit/tipos')
export const painelCredito = (escopo: 'me' | 'global') =>
  api<Painel>(`/api/credits/${escopo}/painel?tz=${encodeURIComponent(fuso())}`)
export const usuariosAdmin = () => api<UsuarioAdmin[]>('/api/admin/usuarios')

/** Micro-USD para texto. Valor pequeno ganha mais casas: US$ 0,000123 não vira US$ 0,00. */
export function usd(micro: number): string {
  const v = micro / 1_000_000
  const casas = v === 0 || Math.abs(v) >= 1 ? 2 : Math.abs(v) >= 0.01 ? 4 : 6
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'USD',
    minimumFractionDigits: casas,
    maximumFractionDigits: casas,
  }).format(v)
}

const fmtEixo = new Intl.NumberFormat('pt-BR', { style: 'currency', currency: 'USD', maximumSignificantDigits: 2 })
/** Rótulo curto de eixo: US$ 0,009 em vez de US$ 0,009000. */
export const usdEixo = (micro: number) => fmtEixo.format(micro / 1_000_000)

export const fmtDataHora = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'medium' })
export const fmtNumero = new Intl.NumberFormat('pt-BR')

/** Rótulo pt-BR dos tipos conhecidos. Tipo novo aparece com o nome cru. */
export const ROTULO_EVENTO: Record<string, string> = {
  user_registered: 'Cadastro',
  login_ok: 'Login',
  login_failed: 'Login falhou',
  conversation_created: 'Conversa criada',
  conversation_deleted: 'Conversa apagada',
  message_sent: 'Mensagem',
  llm_call: 'Chamada de modelo',
  llm_error: 'Erro do modelo',
  tool_call: 'Chamada de tool',
  tool_limit_reached: 'Turno cortado (teto de tools)',
  mcp_tool_failed: 'Turno cortado (MCP falhou)',
  turn_stopped: 'Turno parado pelo usuário',
  tool_toggled: 'Tool ligada/desligada',
  router_decision: 'Roteador',
  router_fallback: 'Roteador (fallback)',
  compaction: 'Compactação',
  share_created: 'Link criado',
  share_revoked: 'Link revogado',
  cap_reached: 'Cap atingido',
}
export const rotuloEvento = (t: string) => ROTULO_EVENTO[t] ?? t

export type OrigemGasto = 'resposta' | 'roteador' | 'compactacao'
export type CustoConversa = {
  total_micro_usd: number
  chamadas: number
  input_tokens: number
  output_tokens: number
  thinking_tokens: number
  cache_read_tokens: number
  por_origem: { origem: OrigemGasto; custo_micro_usd: number; chamadas: number }[]
  saldo: Saldo
}
export const custoDaConversa = (conversa: string) => api<CustoConversa>(`/api/credits/conversas/${conversa}`)
