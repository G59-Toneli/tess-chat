// Conectores (ticket 18, ADR 0010). O callback do Google volta para /conectores?conectado=1 ou ?erro=.
import { api } from '@/lib/api'

export type Conector = {
  provedor: string
  conectado: boolean
  escopos: string[]
  expira_em: string | null
  conectado_em: string | null
}

export const listarConectores = () => api<Conector[]>('/api/connectors')
export const urlDoGoogle = () => api<{ url: string }>('/api/connectors/google/authorize')
export const revogarGoogle = () => api<void>('/api/connectors/google', { method: 'DELETE' })

/** Escopo do Google para rótulo curto. */
export function rotuloEscopo(escopo: string): string {
  if (escopo.endsWith('/gmail.readonly')) return 'Gmail (leitura)'
  if (escopo.endsWith('/drive.readonly')) return 'Drive (leitura)'
  return escopo.replace('https://www.googleapis.com/auth/', '')
}

const ERROS_OAUTH: Record<string, string> = {
  access_denied: 'Você recusou o acesso no Google.',
  state_invalido: 'O link de conexão venceu. Tente de novo.',
  troca_falhou: 'O Google não confirmou a conexão. Tente de novo.',
}

export const textoErroOAuth = (codigo: string) =>
  ERROS_OAUTH[codigo] ?? 'Não foi possível conectar o Google. Tente de novo.'
