import { useCallback, useEffect, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import type { UIMessage } from 'ai'
import { LinkIcon, MessageSquarePlusIcon } from 'lucide-react'
import { AnexoNaMensagem } from '@/components/Anexos'
import { BlocoTool, partesDeTool } from '@/components/BlocoTool'
import { Message, MessageContent, MessageResponse } from '@/components/ai-elements/message'
import { EstadoCarregando, EstadoErro } from '@/components/estados'
import { IconeApp, NOME_APP } from '@/components/Logo'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { ErroApi, juntarTurnos, lerToken } from '@/lib/api'
import { iniciais } from '@/lib/datas'
import { continuarShare, lerSharePublico, type SharePublico } from '@/lib/shares'
import { cn } from '@/lib/utils'

const fmtData = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'long', timeStyle: 'short' })

type Estado = { tipo: 'carregando' } | { tipo: 'ok'; share: SharePublico } | { tipo: 'inexistente' } | { tipo: 'erro' }

/** Conversa pública somente-leitura (/s/:shareId). Sem login, sem sidebar. */
export function Compartilhamento() {
  const { shareId = '' } = useParams()
  const [estado, setEstado] = useState<Estado>({ tipo: 'carregando' })

  const carregar = useCallback(() => {
    setEstado({ tipo: 'carregando' })
    lerSharePublico(shareId).then(
      (share) => setEstado({ tipo: 'ok', share }),
      (e) => setEstado({ tipo: e instanceof ErroApi && e.status === 404 ? 'inexistente' : 'erro' }),
    )
  }, [shareId])

  useEffect(carregar, [carregar])

  useEffect(() => {
    if (estado.tipo === 'ok') document.title = `${estado.share.title} · ${NOME_APP}`
  }, [estado])

  return (
    <div className="flex min-h-dvh flex-col">
      <header className="flex h-14 shrink-0 items-center justify-between border-b px-4">
        <Link to="/" className="flex items-center gap-2 font-semibold">
          <IconeApp className="size-7" /> {NOME_APP}
        </Link>
        <Button variant="outline" size="sm" asChild>
          <Link to={lerToken() ? '/' : '/login'}>{lerToken() ? 'Abrir o app' : 'Entrar'}</Link>
        </Button>
      </header>
      <main className="mx-auto w-full max-w-3xl flex-1 px-4 py-6">
        {estado.tipo === 'carregando' && <EstadoCarregando />}
        {estado.tipo === 'erro' && (
          <EstadoErro mensagem="Não foi possível carregar a conversa." onTentarDeNovo={carregar} />
        )}
        {estado.tipo === 'inexistente' && <LinkIndisponivel />}
        {estado.tipo === 'ok' && <ConversaPublica share={estado.share} shareId={shareId} />}
      </main>
    </div>
  )
}

function LinkIndisponivel() {
  return (
    <Empty>
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <LinkIcon />
        </EmptyMedia>
        <EmptyTitle>Link indisponível</EmptyTitle>
        <EmptyDescription>Este link não existe ou foi revogado por quem compartilhou.</EmptyDescription>
      </EmptyHeader>
      <EmptyContent>
        <Button variant="outline" asChild>
          <Link to="/login">Entrar no {NOME_APP}</Link>
        </Button>
      </EmptyContent>
    </Empty>
  )
}

function ConversaPublica({ share, shareId }: { share: SharePublico; shareId: string }) {
  // Mesmas partes do Chat: texto, anexo (pela rota pública do link) e cards de tool (Rascunho só leitura). Compactação fica fora.
  const visiveis = juntarTurnos(share.messages).filter((m) => m.parts.some(desenhavel))
  return (
    <>
      <div className="mb-6 flex flex-col gap-3 rounded-lg border bg-muted/40 px-4 py-3 md:flex-row md:items-center">
        <div className="min-w-0 flex-1">
          <h1 className="text-xl font-semibold break-words">{share.title}</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Compartilhada por <span className="font-medium text-foreground">{share.shared_by}</span> em{' '}
            {fmtData.format(new Date(share.created_at))}. Somente leitura.
          </p>
        </div>
        <BotaoContinuar shareId={shareId} />
      </div>
      {visiveis.length === 0 ? (
        <p className="py-8 text-center text-sm text-muted-foreground">Esta conversa não tinha mensagens.</p>
      ) : (
        <div className="flex flex-col gap-6">
          {visiveis.map((m) => (
            <LinhaPublica key={m.id} mensagem={m} autor={share.shared_by} />
          ))}
        </div>
      )}
    </>
  )
}

/** Fork (ADR 0020): cópia na conta de quem está logado. Deslogado vai ao login e volta para este link. */
function BotaoContinuar({ shareId }: { shareId: string }) {
  const navigate = useNavigate()
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  async function continuar() {
    const voltar = `/login?proximo=${encodeURIComponent(`/s/${shareId}`)}`
    if (!lerToken()) return navigate(voltar)
    setEnviando(true)
    setErro(null)
    try {
      const { conversation_id } = await continuarShare(shareId)
      navigate(`/c/${conversation_id}`)
    } catch (e) {
      if (e instanceof ErroApi && e.status === 401) return navigate(voltar)
      setErro(e instanceof ErroApi && e.status === 404 ? 'Este link foi revogado.' : 'Não foi possível copiar. Tente de novo.')
      setEnviando(false)
    }
  }

  return (
    <div className="flex flex-col items-end gap-1">
      <Button size="sm" className="w-full md:w-auto" disabled={enviando} onClick={() => void continuar()}>
        {enviando ? <Spinner /> : <MessageSquarePlusIcon />} Continuar esta conversa
      </Button>
      {erro && (
        <p role="alert" className="text-xs text-destructive">
          {erro}
        </p>
      )}
    </div>
  )
}

const desenhavel = (p: UIMessage['parts'][number]) =>
  (p.type === 'text' && p.text.length > 0) || p.type === 'file' || p.type.startsWith('tool-')

function LinhaPublica({ mensagem, autor }: { mensagem: UIMessage; autor: string }) {
  const usuario = mensagem.role === 'user'
  const tools = partesDeTool(mensagem)
  return (
    <div className={cn('flex gap-3', usuario && 'flex-row-reverse')}>
      {usuario ? (
        <Avatar>
          <AvatarFallback className="text-xs">{iniciais(autor)}</AvatarFallback>
        </Avatar>
      ) : (
        <IconeApp className="size-8 rounded-full" />
      )}
      <Message from={usuario ? 'user' : 'assistant'} className="min-w-0 max-w-[85%]">
        <MessageContent>
          {mensagem.parts.map((p, i) => {
            if (p.type === 'text') return p.text ? <MessageResponse key={i}>{p.text}</MessageResponse> : null
            if (p.type === 'file') return <AnexoNaMensagem key={i} parte={p} />
            const parte = tools.find((t) => t === p)
            // Wrapper como no Chat: o Card tem overflow-hidden e, filho direto do flex, encolhia e cortava o corpo.
            return parte ? (
              <div key={i}>
                <BlocoTool parte={parte} somenteLeitura />
              </div>
            ) : null
          })}
        </MessageContent>
      </Message>
    </div>
  )
}
