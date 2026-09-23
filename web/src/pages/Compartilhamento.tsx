import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router'
import { LinkIcon } from 'lucide-react'
import { Message, MessageContent, MessageResponse } from '@/components/ai-elements/message'
import { EstadoCarregando, EstadoErro } from '@/components/estados'
import { IconeApp, NOME_APP } from '@/components/Logo'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { ErroApi, lerToken, type MensagemApi } from '@/lib/api'
import { iniciais } from '@/lib/datas'
import { lerSharePublico, type SharePublico } from '@/lib/shares'
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
        {estado.tipo === 'ok' && <ConversaPublica share={estado.share} />}
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

function ConversaPublica({ share }: { share: SharePublico }) {
  const visiveis = share.messages.filter((m) => m.role !== 'tool' && textoDe(m).length > 0)
  return (
    <>
      <div className="mb-6 rounded-lg border bg-muted/40 px-4 py-3">
        <h1 className="text-xl font-semibold break-words">{share.title}</h1>
        <p className="mt-1 text-sm text-muted-foreground">
          Compartilhada por <span className="font-medium text-foreground">{share.shared_by}</span> em{' '}
          {fmtData.format(new Date(share.created_at))}. Somente leitura.
        </p>
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

const textoDe = (m: MensagemApi) =>
  m.parts.filter((p) => p.type === 'text' && typeof p.text === 'string').map((p) => p.text as string)

function LinhaPublica({ mensagem, autor }: { mensagem: MensagemApi; autor: string }) {
  const usuario = mensagem.role === 'user'
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
          {textoDe(mensagem).map((t, i) => (
            <MessageResponse key={i}>{t}</MessageResponse>
          ))}
        </MessageContent>
      </Message>
    </div>
  )
}
