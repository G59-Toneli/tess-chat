// Servidores MCP (ticket 17, ADR 0009). O header de autenticação vai no cadastro e nunca volta.
import { api } from '@/lib/api'

export type McpTool = { nome: string; descricao: string }
export type McpServidor = {
  id: string
  nome: string
  url: string
  ativo: boolean
  tem_auth: boolean
  created_at: string
  tools: McpTool[]
}
export type McpNovo = { nome: string; url: string; autorizacao: string | null }

const json = (method: string, body: unknown): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

export const listarServidores = () => api<McpServidor[]>('/api/mcp-servers')
export const cadastrarServidor = (novo: McpNovo) => api<McpServidor>('/api/mcp-servers', json('POST', novo))
export const alternarServidor = (id: string, ativo: boolean) =>
  api<McpServidor>(`/api/mcp-servers/${id}`, json('PUT', { ativo }))
export const removerServidor = (id: string) => api<void>(`/api/mcp-servers/${id}`, { method: 'DELETE' })
