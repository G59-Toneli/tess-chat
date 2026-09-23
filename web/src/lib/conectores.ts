// Conectores (ticket 18, ADR 0010) e Rascunho de e-mail (ticket 25, ADR 0013).
// O callback do Google volta para /conectores?conectado=1 ou ?erro=.
import { api } from '@/lib/api'

export type Conector = {
  provedor: string
  conectado: boolean
  escopos: string[]
  expira_em: string | null
  conectado_em: string | null
  conta_email: string | null
  gmail_disponivel: boolean
}

/** Detalhe do 502 no envio: texto em pt-BR e se a saída é reconectar (ticket 29). */
export type ErroEnvio = { mensagem: string; reconectar: boolean }

export const ehErroEnvio = (x: unknown): x is ErroEnvio =>
  typeof x === 'object' && x !== null && typeof (x as ErroEnvio).mensagem === 'string'

export const listarConectores = () => api<Conector[]>('/api/connectors')
export const urlDoGoogle = () => api<{ url: string }>('/api/connectors/google/authorize')
export const revogarGoogle = () => api<void>('/api/connectors/google', { method: 'DELETE' })

export const ESCOPO_ENVIO = 'https://www.googleapis.com/auth/gmail.send'

/** Conector ligado antes do ticket 25: lê, mas não tem gmail_send até reconectar. */
export const semEnvio = (c: Conector) => c.conectado && !c.escopos.includes(ESCOPO_ENVIO)

export type EstadoRascunho = 'pendente' | 'enviado' | 'descartado'

export type Rascunho = {
  id: string
  para: string
  assunto: string
  corpo: string
  thread_id: string | null
  em_resposta: boolean
  estado: EstadoRascunho
  decidido_em: string | null
}

const DRAFTS = '/api/connectors/google/drafts'
export const lerRascunho = (id: string) => api<Rascunho>(`${DRAFTS}/${id}`)
export const enviarRascunho = (id: string) => api<Rascunho>(`${DRAFTS}/${id}/enviar`, { method: 'POST' })
export const descartarRascunho = (id: string) => api<Rascunho>(`${DRAFTS}/${id}/descartar`, { method: 'POST' })

/** Escopo do Google para rótulo curto. */
export function rotuloEscopo(escopo: string): string {
  if (escopo.endsWith('/gmail.readonly')) return 'Gmail (leitura)'
  if (escopo.endsWith('/drive.readonly')) return 'Drive (leitura)'
  if (escopo.endsWith('/gmail.send')) return 'Gmail (envio com confirmação)'
  return escopo.replace('https://www.googleapis.com/auth/', '')
}

const ERROS_OAUTH: Record<string, string> = {
  access_denied: 'Você recusou o acesso no Google.',
  state_invalido: 'O link de conexão venceu. Tente de novo.',
  troca_falhou: 'O Google não confirmou a conexão. Tente de novo.',
}

export const textoErroOAuth = (codigo: string) =>
  ERROS_OAUTH[codigo] ?? 'Não foi possível conectar o Google. Tente de novo.'
