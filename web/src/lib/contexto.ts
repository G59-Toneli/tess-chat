// Janela de contexto da Conversa (ticket 32): quanto o próximo turno carrega.
import { api } from '@/lib/api'

export type Contexto = { usado: number; limite: number; limiar_compactacao: number; modelo: string }

export const lerContexto = (conversa: string) => api<Contexto>(`/api/conversations/${conversa}/contexto`)

const compacto = new Intl.NumberFormat('pt-BR', { notation: 'compact', maximumFractionDigits: 1 })

/** 12400 vira "12,4 mil"; 1048576 vira "1 mi". */
export const tokens = (n: number) => compacto.format(n)

/** Fração usada, entre 0 e 1. */
export const fracao = ({ usado, limite }: Contexto) => (limite > 0 ? Math.min(usado / limite, 1) : 0)

export type Faixa = 'normal' | 'alerta' | 'critico'

/** Até 70 % normal, de 70 a 90 % alerta, acima de 90 % crítico. */
export const faixa = (f: number): Faixa => (f > 0.9 ? 'critico' : f >= 0.7 ? 'alerta' : 'normal')

export function resumo(c: Contexto): string {
  const pct = (fracao(c) * 100).toLocaleString('pt-BR', { maximumFractionDigits: 1 })
  const restante = tokens(Math.max(c.limite - c.usado, 0))
  return `Contexto: ${tokens(c.usado)} de ${tokens(c.limite)} tokens (${pct} %) · restante ${restante} · compacta em ${tokens(c.limiar_compactacao)} · ${c.modelo}`
}
