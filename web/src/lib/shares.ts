// Compartilhamento (ADR 0008): criar, listar, revogar e ler o link público.
import { api, type MensagemApi } from '@/lib/api'

export type Share = { id: string; url: string; conversation_id: string; title: string; created_at: string }
export type SharePublico = { title: string; shared_by: string; created_at: string; messages: MensagemApi[] }

export const urlAbsoluta = (s: Share) => new URL(s.url, window.location.origin).toString()
export const criarShare = (conversaId: string) =>
  api<Share>(`/api/conversations/${conversaId}/share`, { method: 'POST' })
export const listarShares = () => api<Share[]>('/api/shares')
export const revogarShare = (id: string) => api<void>(`/api/shares/${id}`, { method: 'DELETE' })
/** Público: sem token, para o link abrir igual em janela anônima. */
export const lerSharePublico = (id: string) => api<SharePublico>(`/api/s/${id}`, { semAuth: true })
/** Cópia da conversa do link para a conta logada. Devolve o id da Conversa nova. */
export const continuarShare = (id: string) =>
  api<{ conversation_id: string }>(`/api/s/${id}/fork`, { method: 'POST' })

/** Copia para a área de transferência. Falso quando o browser recusa. */
export async function copiar(texto: string): Promise<boolean> {
  try {
    await navigator.clipboard.writeText(texto)
    return true
  } catch {
    return false
  }
}
