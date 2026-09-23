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

// Atalhos de 1 clique: os dois aceitam registro dinâmico (DCR). Ticket 52.
export const ATALHOS_OAUTH = [
  { nome: 'Notion', url: 'https://mcp.notion.com/mcp' },
  { nome: 'Stripe', url: 'https://mcp.stripe.com' },
]

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
  api<{ id: string; url: string }>('/api/mcp-servers/oauth/iniciar', json('POST', pedido))
export const alternarServidor = (id: string, ativo: boolean) =>
  api<McpServidor>(`/api/mcp-servers/${id}`, json('PUT', { ativo }))
export const removerServidor = (id: string) => api<void>(`/api/mcp-servers/${id}`, { method: 'DELETE' })
