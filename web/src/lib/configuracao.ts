// Configuração por Usuário e por Conversa (ticket 14). null = herda do escopo de cima.
import { api } from '@/lib/api'

export type Configuracao = {
  modelo: string
  nivel_raciocinio: string
  compactacao_limiar: number
  roteador_limiar: number
  tool_calls_limite: number
}
export type Valores = { [K in keyof Configuracao]: Configuracao[K] | null }
export type RespostaConfig = { valores: Valores; herdada: Configuracao; efetiva: Configuracao }

export const MODELOS = [
  { valor: 'gemini-3.8-flash', rotulo: 'Gemini 3.8 Flash' },
  { valor: 'gemini-3.1-flash-lite', rotulo: 'Gemini 3.1 Flash-Lite (mais barato)' },
]
export const NIVEIS = [
  { valor: 'minimal', rotulo: 'Mínimo' },
  { valor: 'low', rotulo: 'Baixo' },
  { valor: 'medium', rotulo: 'Médio' },
  { valor: 'high', rotulo: 'Alto' },
]

const caminho = (conversa: string | null) => (conversa ? `/api/conversations/${conversa}/settings` : '/api/settings')

export const lerConfig = (conversa: string | null) => api<RespostaConfig>(caminho(conversa))

export const salvarConfig = (conversa: string | null, mudancas: Partial<Valores>) =>
  api<RespostaConfig>(caminho(conversa), {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(mudancas),
  })

export const definirCap = (usuario: string, cap_micro_usd: number) =>
  api<{ user_id: string; cap_micro_usd: number }>(`/api/admin/usuarios/${usuario}/cap`, {
    method: 'PUT',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ cap_micro_usd }),
  })
