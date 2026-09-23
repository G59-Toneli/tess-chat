// Cliente da API: token JWT no localStorage, header Bearer, 401 volta para o login.
import type { UIMessage } from 'ai'

const CHAVE_TOKEN = 'token'

export const CONTA_DEMO = { email: 'demo@toneli.dev.br', senha: 'demo12345' }

export type Usuario = { id: string; email: string; is_superuser: boolean }
export type Conversa = { id: string; title: string; created_at: string; updated_at: string }
export type MensagemApi = {
  id: number
  role: string
  parts: Record<string, unknown>[]
  created_at: string
}

export function lerToken(): string | null {
  try {
    return localStorage.getItem(CHAVE_TOKEN)
  } catch {
    return null
  }
}

export function sair(): void {
  try {
    localStorage.removeItem(CHAVE_TOKEN)
  } catch {
    // Sem storage: nada a limpar.
  }
  window.location.assign('/login')
}

export function authHeader(): Record<string, string> {
  const token = lerToken()
  return token ? { Authorization: `Bearer ${token}` } : {}
}

export class ErroApi extends Error {
  status: number
  detail: unknown
  constructor(status: number, detail: unknown) {
    super(typeof detail === 'string' ? detail : `HTTP ${status}`)
    this.status = status
    this.detail = detail
  }
}

export async function api<T>(caminho: string, init: RequestInit = {}): Promise<T> {
  const r = await fetch(caminho, { ...init, headers: { ...authHeader(), ...init.headers } })
  if (r.status === 401 && lerToken()) sair()
  if (!r.ok) {
    const corpo = await r.json().catch(() => ({}))
    throw new ErroApi(r.status, corpo.detail)
  }
  return (r.status === 204 ? undefined : await r.json()) as T
}

const json = (body: unknown): RequestInit => ({
  headers: { 'Content-Type': 'application/json' },
  body: JSON.stringify(body),
})

// Códigos do FastAPI-Users para texto em pt-BR.
const ERROS_AUTH: Record<string, string> = {
  LOGIN_BAD_CREDENTIALS: 'E-mail ou senha incorretos.',
  REGISTER_USER_ALREADY_EXISTS: 'Já existe uma conta com esse e-mail.',
  REGISTER_INVALID_PASSWORD: 'Senha inválida.',
}

export function textoErroAuth(e: unknown): string {
  if (e instanceof ErroApi) {
    if (typeof e.detail === 'string' && ERROS_AUTH[e.detail]) return ERROS_AUTH[e.detail]
    if (e.status === 422) return 'Confira o e-mail e a senha.'
  }
  return 'Não foi possível falar com o servidor. Tente de novo.'
}

export async function entrar(email: string, senha: string): Promise<void> {
  const r = await api<{ access_token: string }>('/auth/jwt/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username: email, password: senha }),
  })
  localStorage.setItem(CHAVE_TOKEN, r.access_token)
}

/** Cadastro não devolve token: cadastra e entra em seguida. */
export async function cadastrar(email: string, senha: string): Promise<void> {
  await api('/auth/register', { method: 'POST', ...json({ email, password: senha }) })
  await entrar(email, senha)
}

// Pública: o Login lê antes de ter token (ticket 34).
export const configPublica = () => api<{ demo: boolean; env: string }>('/api/config-publica')
export const eu = () => api<Usuario>('/users/me')
export const listarConversas = () => api<Conversa[]>('/api/conversations')
export const criarConversa = (title: string) =>
  api<Conversa>('/api/conversations', { method: 'POST', ...json({ title }) })
export const renomearConversa = (id: string, title: string) =>
  api<Conversa>(`/api/conversations/${id}`, { method: 'PATCH', ...json({ title }) })
export const apagarConversa = (id: string) => api<void>(`/api/conversations/${id}`, { method: 'DELETE' })
export const listarMensagens = (id: string) => api<MensagemApi[]>(`/api/conversations/${id}/messages`)

/** Id (do banco) da pergunta do turno que fez o Resumo vigente, ou null sem Resumo. */
export function lerCorte(conversaId: string): Promise<number | null> {
  return fetch(`/api/chat/${conversaId}/compactacao`, { headers: authHeader() })
    .then((r) => (r.ok ? r.json() : { turno_message_id: null }))
    .then((j: { turno_message_id: number | null }) => j.turno_message_id)
    .catch(() => null)
}

/** Um turno com tool vira várias linhas assistant seguidas. Junto numa só, como no stream.
 * Fica o id da última linha: é ela que tem o uso. Linhas `tool` ficam fora. */
export function juntarTurnos(linhas: MensagemApi[]): UIMessage[] {
  const mensagens: UIMessage[] = []
  for (const m of linhas.filter((l) => l.role === 'user' || l.role === 'assistant')) {
    const anterior = mensagens.at(-1)
    const parts = m.parts as UIMessage['parts']
    if (m.role === 'assistant' && anterior?.role === 'assistant')
      mensagens[mensagens.length - 1] = { ...anterior, id: String(m.id), parts: [...anterior.parts, ...parts] }
    else mensagens.push({ id: String(m.id), role: m.role as 'user' | 'assistant', parts })
  }
  return mensagens
}

const ERRO_PROVEDOR = 'O provedor do modelo falhou. Tente de novo.'

/** Erro do useChat para texto em pt-BR. O 502 da API já vem em pt-BR no `detail`. */
export function textoErroChat(e: Error & { statusCode?: number }): string {
  if (e.statusCode === 401) return 'Sua sessão expirou. Entre de novo.'
  try {
    const detail = JSON.parse(e.message).detail
    if (typeof detail === 'string' && e.statusCode === 502) return detail
  } catch {
    // Erro no meio do stream: texto do provedor, em inglês.
  }
  return ERRO_PROVEDOR
}

// Anexos (ticket 09). A Mensagem leva só a referência `/api/attachments/{id}`.
export type Anexo = { id: string; filename: string; mime_type: string; size_bytes: number; url: string }
export const ACEITOS = 'image/png,image/jpeg,image/webp,application/pdf'
export const LIMITE_ANEXO = 20 * 1024 * 1024

/** Sobe um arquivo. `dados` é o data URL que o prompt-input entrega. */
export async function enviarAnexo(dados: string, nome: string): Promise<Anexo> {
  const blob = await (await fetch(dados)).blob()
  const form = new FormData()
  form.append('file', blob, nome)
  return api<Anexo>('/api/attachments', { method: 'POST', body: form })
}

export function textoErroAnexo(e: unknown): string {
  if (e instanceof ErroApi && e.status === 415) return 'Tipo não permitido. Envie PNG, JPG, WEBP ou PDF.'
  if (e instanceof ErroApi && e.status === 413) return 'Arquivo acima de 20 MB.'
  return 'Não foi possível enviar o anexo. Tente de novo.'
}
