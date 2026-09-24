// Tool por API (tickets 59 e 60, ADR 0024). O segredo da auth vai no cadastro e nunca volta.
import { api } from '@/lib/api'

export type TipoParametro = 'string' | 'number' | 'integer' | 'boolean'
export type Parametro = { nome: string; tipo: TipoParametro; descricao: string; obrigatorio: boolean }
export type Auth = { tipo: 'nenhuma' | 'header' | 'bearer'; nome?: string; valor?: string; token?: string }
export type Metodo = 'GET' | 'POST'
/** Body de POST /api/api-tools e de /testar. `exemplo` vai como texto: o back converte pelo tipo. */
export type ApiToolNova = {
  nome: string
  descricao: string
  metodo: Metodo
  url: string
  parametros: Parametro[]
  corpo: unknown
  auth: Auth
  exemplo: Record<string, unknown>
}
export type ApiTool = {
  id: string
  nome: string
  tool_nome: string
  descricao: string
  metodo: Metodo
  url: string
  parametros: Parametro[]
  corpo: unknown
  auth_tipo: string
  created_at: string
}
export type Teste = { status: number; corpo_cortado: string; ms: number }

export const LIMITE_NOME = 40
export const LIMITE_DESCRICAO = 1000

// Mesmo regex do back (PLACEHOLDER em api/app/api_tools.py).
const PLACEHOLDER = /\{([A-Za-z_][A-Za-z0-9_]*)\}/g

/** Nomes dos `{param}` num texto, na ordem em que aparecem, sem repetir. */
export function placeholders(texto: string): string[] {
  return [...new Set([...texto.matchAll(PLACEHOLDER)].map((m) => m[1]))]
}

// Segmentos que não dizem nada sobre a API.
const GENERICOS = new Set(['api', 'www', 'ws', 'json', 'rest', 'v1', 'v2', 'v3', 'v4'])
const SEGUNDO_NIVEL = new Set(['com', 'net', 'org', 'gov', 'edu', 'co'])

/** Nome sugerido de host e path: `brasilapi.com.br/api/cnpj/v1/{cnpj}` vira `brasilapi_cnpj`. */
export function nomeSugerido(url: string): string {
  let u: URL
  try {
    u = new URL(url.replace(PLACEHOLDER, 'x'))
  } catch {
    return ''
  }
  // Tira o TLD e o "com" de "com.br": viacep.com.br vira viacep.
  const rotulos = u.hostname.split('.').filter((p) => !GENERICOS.has(p))
  if (rotulos.length > 1) rotulos.pop()
  if (rotulos.length > 1 && SEGUNDO_NIVEL.has(rotulos[rotulos.length - 1])) rotulos.pop()
  const host = rotulos[rotulos.length - 1] ?? ''
  const segmento = decodeURIComponent(url.split('?')[0].replace(/^https?:\/\/[^/]*/, ''))
    .split('/')
    .find((s) => s && !s.includes('{') && !GENERICOS.has(s.toLowerCase()))
  const slug = [host, segmento]
    .filter(Boolean)
    .join('_')
    .toLowerCase()
    .normalize('NFD')
    .replace(/[^a-z0-9]+/g, '_')
    .replace(/^[^a-z]+|_+$/g, '')
  return slug.slice(0, LIMITE_NOME).replace(/_+$/, '')
}

const ROTULOS: Record<string, string> = { viacep: 'ViaCEP', open_meteo: 'Open-Meteo', cnpj: 'CNPJ' }
export const rotuloModelo = (nome: string) => ROTULOS[nome] ?? nome

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const listarApiTools = () => api<ApiTool[]>('/api/api-tools')
export const listarModelos = () => api<ApiToolNova[]>('/api/api-tools/modelos')
export const testarApiTool = (nova: ApiToolNova) => api<Teste>('/api/api-tools/testar', json('POST', nova))
export const cadastrarApiTool = (nova: ApiToolNova) => api<ApiTool>('/api/api-tools', json('POST', nova))
export const removerApiTool = (id: string) => api<void>(`/api/api-tools/${id}`, { method: 'DELETE' })
