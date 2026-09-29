// Mensagens e erros da Ligação (docs/PROTOCOLO-LIGACAO.md). Toda recusa vira texto em pt-BR.
import { ErroApi, api, json } from '@/lib/api'

export type Origem = 'usuario' | 'agente'
export type MotivoFim = 'desligou' | 'limite' | 'erro' | 'queda'

export type MensagemServidor =
  | { tipo: 'pronto'; limite_s?: number }
  | { tipo: 'transcricao'; origem: Origem; texto: string; final: boolean }
  | { tipo: 'interrompido' }
  | { tipo: 'fim'; motivo: MotivoFim }
  | { tipo: 'erro'; mensagem: string }

export type MensagemBrowser =
  | { tipo: 'frame'; jpeg: string }
  | { tipo: 'tela'; ativa: boolean }
  | { tipo: 'desligar' }

const CAP = 'Seu crédito não cobre uma ligação de 9 minutos. Veja o saldo e o limite em Créditos.'
const OCUPADA = 'Esta conversa já tem uma resposta em andamento, ou você já está em outra ligação.'
const TETO = 'Muitas ligações ao mesmo tempo agora. Tente de novo em alguns minutos.'

/** Recusa do `POST /api/voz/ticket` por status HTTP. */
const POR_STATUS: Record<number, string> = {
  402: CAP,
  404: 'Conversa não encontrada.',
  409: OCUPADA,
  429: TETO,
}

/** Recusa depois do upgrade, por close code do WebSocket. */
const POR_CLOSE_CODE: Record<number, string> = {
  4401: 'O acesso à ligação expirou. Tente ligar de novo.',
  4402: CAP,
  4409: OCUPADA,
  4429: TETO,
  4500: 'O serviço de voz não respondeu. Tente de novo.',
}

const POR_MOTIVO: Record<MotivoFim, string> = {
  desligou: 'Ligação encerrada.',
  limite: 'O tempo da ligação acabou (9 minutos).',
  erro: 'A ligação terminou por um erro no servidor.',
  queda: 'A ligação caiu.',
}

export class ErroLigacao extends Error {
  /** Falta de crédito: a tela oferece o link para Créditos. */
  cap: boolean
  constructor(mensagem: string, cap = false) {
    super(mensagem)
    this.cap = cap
  }
}

export async function pedirTicket(conversaId: string): Promise<string> {
  try {
    const r = await api<{ ticket: string }>('/api/voz/ticket', { method: 'POST', ...json({ conversa_id: conversaId }) })
    return r.ticket
  } catch (e) {
    if (e instanceof ErroApi && POR_STATUS[e.status]) throw new ErroLigacao(POR_STATUS[e.status], e.status === 402)
    throw new ErroLigacao('Não foi possível falar com o servidor. Tente de novo.')
  }
}

export function urlWs(ticket: string): string {
  const esquema = location.protocol === 'https:' ? 'wss' : 'ws'
  return `${esquema}://${location.host}/api/voz/ws?ticket=${encodeURIComponent(ticket)}`
}

export const textoFechamento = (codigo: number): string | undefined => POR_CLOSE_CODE[codigo]
export const capNoFechamento = (codigo: number) => codigo === 4402
export const textoFim = (motivo: MotivoFim): string => POR_MOTIVO[motivo] ?? POR_MOTIVO.queda

export const TEXTO_MICROFONE = 'Sem acesso ao microfone. Libere o microfone para este site e tente de novo.'
export const TEXTO_QUEDA = POR_MOTIVO.queda
