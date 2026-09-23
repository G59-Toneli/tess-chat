// Datas no fuso do browser (docs/UI-GUIA.md).

export type Grupo<T> = { rotulo: string; itens: T[] }

const DIA = 24 * 60 * 60 * 1000

// REVISAR(human): agrupa por dia de calendário local, não por "24 h atrás".
// Hoje = desde a meia-noite; Ontem = dia anterior; 7 dias = até 7 meias-noites atrás.
// Grupo vazio some. A ordem de entrada (mais recente primeiro) é mantida.
export function agruparPorData<T extends { updated_at: string }>(itens: T[], agora = new Date()): Grupo<T>[] {
  const meiaNoite = new Date(agora.getFullYear(), agora.getMonth(), agora.getDate()).getTime()
  const grupos: Grupo<T>[] = [
    { rotulo: 'Hoje', itens: [] },
    { rotulo: 'Ontem', itens: [] },
    { rotulo: 'Últimos 7 dias', itens: [] },
    { rotulo: 'Mais antigas', itens: [] },
  ]
  for (const item of itens) {
    const t = new Date(item.updated_at).getTime()
    const i = t >= meiaNoite ? 0 : t >= meiaNoite - DIA ? 1 : t >= meiaNoite - 7 * DIA ? 2 : 3
    grupos[i].itens.push(item)
  }
  return grupos.filter((g) => g.itens.length > 0)
}

const fmtHora = new Intl.DateTimeFormat('pt-BR', { hour: '2-digit', minute: '2-digit' })

export const hora = (d: Date) => fmtHora.format(d)

/** Iniciais do avatar a partir do e-mail. */
export function iniciais(email: string): string {
  const nome = email.split('@')[0].replace(/[^a-zA-Z0-9]/g, ' ').trim()
  const partes = nome.split(/\s+/)
  const txt = partes.length > 1 ? partes[0][0] + partes[1][0] : nome.slice(0, 2)
  return txt.toUpperCase() || '?'
}
