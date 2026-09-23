// Compartilhamento (ADR 0008): criar, listar, revogar e ler o link público.
import { authHeader, ErroApi, type MensagemApi } from '@/lib/api'

export type Share = { id: string; url: string; conversation_id: string; title: string; created_at: string }
export type SharePublico = { title: string; shared_by: string; created_at: string; messages: MensagemApi[] }

async function pedir<T>(caminho: string, init: RequestInit = {}, comAuth = true): Promise<T> {
  const r = await fetch(caminho, { ...init, headers: comAuth ? authHeader() : {} })
  if (!r.ok) throw new ErroApi(r.status, (await r.json().catch(() => ({}))).detail)
  return (r.status === 204 ? undefined : await r.json()) as T
}

export const urlAbsoluta = (s: Share) => new URL(s.url, window.location.origin).toString()
export const criarShare = (conversaId: string) =>
  pedir<Share>(`/api/conversations/${conversaId}/share`, { method: 'POST' })
export const listarShares = () => pedir<Share[]>('/api/shares')
export const revogarShare = (id: string) => pedir<void>(`/api/shares/${id}`, { method: 'DELETE' })
/** Público: sem token, para o link abrir igual em janela anônima. */
export const lerSharePublico = (id: string) => pedir<SharePublico>(`/api/s/${id}`, {}, false)
/** Cópia da conversa do link para a conta logada. Devolve o id da Conversa nova. */
export const continuarShare = (id: string) =>
  pedir<{ conversation_id: string }>(`/api/s/${id}/fork`, { method: 'POST' })

/** Copia para a área de transferência. Falso quando o browser recusa. */
export async function copiar(texto: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(texto)
    return true
  } catch {
    return false
  }
}
