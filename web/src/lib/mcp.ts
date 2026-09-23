// Servidores MCP (ticket 17, ADR 0009). O header de autenticação vai no cadastro e nunca volta.
import { api } from '@/lib/api'

export type McpTool = { nome: string; descricao: string }
export type McpServidor = {
  id: string
  nome: string
  url: string
  ativo: boolean
  tem_auth: boolean
  estado: 'ok' | 'aguardando_oauth' | 'expirado'
  oauth: boolean
  created_at: string
  tools: McpTool[]
}
export type McpNovo = { nome: string; url: string; autorizacao: string | null }
export type McpOAuth = { nome: string; url: string; sid?: string }
// Caminho que o iniciar detectou (ticket 56). Só o modo oauth grava linha no banco.
export type McpDeteccao = { modo: 'oauth'; id: string; url: string } | { modo: 'sem_auth' } | { modo: 'token' }

// Catálogo de 1 clique: os dois aceitam registro dinâmico (DCR). Tickets 52 e 56.
export const CATALOGO_MCP = [
  { nome: 'Notion', url: 'https://mcp.notion.com/mcp', descricao: 'Páginas e bancos de dados.' },
  { nome: 'Stripe', url: 'https://mcp.stripe.com', descricao: 'Clientes, cobranças e links de pagamento.' },
] as const

const PREFIXOS_HOST = new Set(['mcp', 'api', 'www'])

/** Nome sugerido a partir do host: `mcp.linear.app` vira "Linear". IP e host inválido voltam como estão. */
export function nomeDoHost(url: string): string {
  let host: string
  try {
    host = new URL(url).hostname
  } catch {
    return 'Servidor'
  }
  if (/^[\d.]+$/.test(host) || host.includes(':')) return host
  const partes = host.split('.').filter((p) => !PREFIXOS_HOST.has(p))
  const base = partes.length > 1 ? partes[partes.length - 2] : (partes[0] ?? host)
  return base.charAt(0).toUpperCase() + base.slice(1)
}

/** Nome que ainda não existe entre os servidores do Usuário: "Linear", "Linear 2", "Linear 3"... */
export function nomeLivre(base: string, existentes: string[]): string {
  const usados = new Set(existentes)
  if (!usados.has(base)) return base
  let n = 2
  while (usados.has(`${base} ${n}`)) n++
  return `${base} ${n}`
}

const ERROS_OAUTH: Record<string, string> = {
  access_denied: 'Você recusou o acesso no servidor.',
  state_invalido: 'O link de conexão venceu. Tente de novo.',
  pkce_ausente: 'A conexão venceu ou começou em outro navegador. Tente de novo.',
  troca_falhou: 'O servidor não confirmou a conexão. Tente de novo.',
  listagem_falhou: 'Conectou, mas o servidor não listou as tools. Tente reconectar.',
}

export const textoErroOAuthMcp = (codigo: string) =>
  ERROS_OAUTH[codigo] ?? 'Não foi possível conectar o servidor MCP. Tente de novo.'

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const listarServidores = () => api<McpServidor[]>('/api/mcp-servers')
export const cadastrarServidor = (novo: McpNovo) => api<McpServidor>('/api/mcp-servers', json('POST', novo))
export const iniciarOAuth = (pedido: McpOAuth) =>
  api<McpDeteccao>('/api/mcp-servers/oauth/iniciar', json('POST', pedido))
export const alternarServidor = (id: string, ativo: boolean) =>
  api<McpServidor>(`/api/mcp-servers/${id}`, json('PUT', { ativo }))
export const removerServidor = (id: string) => api<void>(`/api/mcp-servers/${id}`, { method: 'DELETE' })
