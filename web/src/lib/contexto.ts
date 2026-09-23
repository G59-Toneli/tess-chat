// Janela de contexto da Conversa (ticket 32): quanto o próximo turno carrega.
import { api } from '@/lib/api'

export type Contexto = { usado: number; limite: number; limiar_compactacao: number; modelo: string }

export const lerContexto = (conversa: string) => api<Contexto>(`/api/conversations/${conversa}/contexto`)

const compacto = new Intl.NumberFormat('pt-BR', { notation: 'compact', maximumFractionDigits: 1 })

/** 12400 vira "12,4 mil"; 1048576 vira "1 mi". */
export const tokens = (n: number) => compacto.format(n)

// REVISAR(human): a base é o limiar de Compactação, não a janela do modelo. A janela do Gemini
// é de ~1 mi e a Compactação dispara bem antes (padrão 100 mil), então contra a janela a rosca
// ficava sempre quase vazia. Rosca cheia = o próximo turno resume o histórico antigo.
/** Fração até a Compactação, entre 0 e 1. */
export const fracao = ({ usado, limiar_compactacao }: Contexto) =>
  limiar_compactacao > 0 ? Math.min(usado / limiar_compactacao, 1) : 0

export type Faixa = 'normal' | 'alerta' | 'critico'

/** Até 70 % normal, de 70 a 90 % alerta, acima de 90 % crítico. */
export const faixa = (f: number): Faixa => (f > 0.9 ? 'critico' : f >= 0.7 ? 'alerta' : 'normal')

export function resumo(c: Contexto): string {
  const janela = `janela do modelo ${tokens(c.limite)} · ${c.modelo}`
  if (c.usado > c.limiar_compactacao)
    return `Contexto: ${tokens(c.usado)} tokens, acima do limiar de compactação (${tokens(c.limiar_compactacao)}): o histórico antigo vai ser resumido · ${janela}`
  const pct = (fracao(c) * 100).toLocaleString('pt-BR', { maximumFractionDigits: 1 })
  const restante = tokens(c.limiar_compactacao - c.usado)
  return `Contexto: ${tokens(c.usado)} de ${tokens(c.limiar_compactacao)} tokens até compactar (${pct} %) · faltam ${restante} · ${janela}`
}
