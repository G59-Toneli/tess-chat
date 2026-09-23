import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { useNavigate, useParams } from 'react-router'
import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport, type ChatStatus, type UIMessage } from 'ai'
import { toast } from 'sonner'
import { MessageSquareIcon } from 'lucide-react'
import { Conversation, ConversationContent, ConversationScrollButton } from '@/components/ai-elements/conversation'
import { Message, MessageContent, MessageResponse } from '@/components/ai-elements/message'
import {
  PromptInput,
  PromptInputBody,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
  type PromptInputMessage,
} from '@/components/ai-elements/prompt-input'
import { Shimmer } from '@/components/ai-elements/shimmer'
import { EstadoCarregando, EstadoErro } from '@/components/estados'
import { IconeApp } from '@/components/Logo'
import { MarcadorCompactacao } from '@/components/MarcadorCompactacao'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { useContextoApp } from '@/layout/AppLayout'
import { authHeader, criarConversa, listarMensagens, sair, textoErroChat } from '@/lib/api'
import { hora, iniciais } from '@/lib/datas'
import { cn } from '@/lib/utils'

const SUGESTOES = [
  'Explique o que é um LLM em três frases.',
  'Me dê ideias de nome para um app de tarefas.',
  'Escreva um e-mail curto pedindo reunião na sexta.',
]

// Texto digitado em "/" antes de a Conversa existir. O chat da nova rota consome uma vez.
const pendentes = new Map<string, string>()

function tituloDe(texto: string): string {
  const t = texto.trim().replace(/\s+/g, ' ')
  return t.length > 60 ? `${t.slice(0, 57)}…` : t
}

export function Chat() {
  const { id } = useParams()
  return id ? <CarregarConversa key={id} id={id} /> : <ChatNovo />
}

// REVISAR(human): em "/" a Conversa ainda não existe. Crio ela com o título tirado
// do primeiro texto, guardo o texto em `pendentes` e navego para /c/:id. O chat de lá
// envia uma vez. Alternativa descartada: criar a Conversa dentro do transporte do
// useChat; a troca de rota remonta o componente e mata o stream.
function ChatNovo() {
  const navigate = useNavigate()
  const { recarregarConversas } = useContextoApp()
  const [criando, setCriando] = useState(false)

  async function comecar(texto: string) {
    if (!texto.trim() || criando) return
    setCriando(true)
    try {
      const conv = await criarConversa(tituloDe(texto))
      pendentes.set(conv.id, texto)
      void recarregarConversas()
      navigate(`/c/${conv.id}`)
    } catch {
      toast.error('Não foi possível criar a conversa. Tente de novo.')
      setCriando(false)
    }
  }

  return (
    <LayoutChat
      entrada={<Entrada status={criando ? 'submitted' : 'ready'} onEnviar={comecar} />}
    >
      <TelaVazia onEscolher={comecar} />
    </LayoutChat>
  )
}

function CarregarConversa({ id }: { id: string }) {
  const [inicial, setInicial] = useState<{ mensagens: UIMessage[]; horarios: Map<string, Date> } | null>(null)
  const [erro, setErro] = useState(false)

  const carregar = useCallback(async () => {
    setErro(false)
    try {
      const linhas = await listarMensagens(id)
      const visiveis = linhas.filter((m) => m.role === 'user' || m.role === 'assistant')
      setInicial({
        mensagens: visiveis.map((m) => ({
          id: String(m.id),
          role: m.role as 'user' | 'assistant',
          parts: m.parts as UIMessage['parts'],
        })),
        horarios: new Map(visiveis.map((m) => [String(m.id), new Date(m.created_at)])),
      })
    } catch {
      setErro(true)
    }
  }, [id])

  useEffect(() => {
    void carregar()
  }, [carregar])

  if (erro)
    return (
      <LayoutChat>
        <EstadoErro mensagem="Não foi possível carregar a conversa." onTentarDeNovo={carregar} />
      </LayoutChat>
    )
  if (!inicial)
    return (
      <LayoutChat>
        <EstadoCarregando />
      </LayoutChat>
    )
  return <ChatConversa id={id} inicial={inicial.mensagens} horarios={inicial.horarios} />
}

function ChatConversa({ id, inicial, horarios }: { id: string; inicial: UIMessage[]; horarios: Map<string, Date> }) {
  const { usuario, recarregarConversas } = useContextoApp()
  const transport = useMemo(
    // headers como função: lê o token na hora do envio.
    () => new DefaultChatTransport({ api: `/api/chat/${id}`, headers: () => authHeader() }),
    [id],
  )
  const { messages, sendMessage, status, stop, error, regenerate, clearError } = useChat({
    id,
    messages: inicial,
    transport,
    onFinish: () => void recarregarConversas(),
  })

  // Envia o texto que veio de "/". O setTimeout sobrevive ao StrictMode: o cleanup do
  // useChat chama stop() e abortaria um envio feito direto no primeiro efeito.
  useEffect(() => {
    const texto = pendentes.get(id)
    if (texto === undefined) return
    const t = setTimeout(() => {
      pendentes.delete(id)
      void sendMessage({ text: texto })
    })
    return () => clearTimeout(t)
  }, [id, sendMessage])

  useEffect(() => {
    if (!error) return
    const e = error as Error & { statusCode?: number }
    if (e.statusCode === 401) return sair()
    toast.error(textoErroChat(e), {
      id: 'erro-chat',
      action: {
        label: 'Tentar de novo',
        onClick: () => {
          clearError()
          void regenerate()
        },
      },
    })
  }, [error, clearError, regenerate])

  // Mensagem nova não tem created_at do banco: vale a hora em que apareceu.
  const hs = useRef(horarios)
  for (const m of messages) if (!hs.current.has(m.id)) hs.current.set(m.id, new Date())

  const ultima = messages.at(-1)
  const semTexto = (m?: UIMessage) => !m?.parts.some((p) => p.type === 'text' && p.text)
  const pensando = status === 'submitted' || (status === 'streaming' && ultima?.role === 'assistant' && semTexto(ultima))
  const visiveis = messages.filter((m) => m.role === 'user' || !semTexto(m))

  function enviar(texto: string) {
    if (!texto.trim() || status === 'submitted' || status === 'streaming') return
    if (error) clearError()
    void sendMessage({ text: texto })
  }

  return (
    <LayoutChat entrada={<Entrada status={status} onEnviar={enviar} onParar={stop} />}>
      {visiveis.length === 0 && !pensando ? (
        <TelaVazia onEscolher={enviar} />
      ) : (
        <>
          {visiveis.map((m) => (
            <MarcadorCompactacao key={m.id} conversaId={id} mensagemId={m.id}><LinhaMensagem key={m.id} mensagem={m} quando={hs.current.get(m.id)} email={usuario?.email} /></MarcadorCompactacao>
          ))}
          {pensando && <Pensando />}
        </>
      )}
    </LayoutChat>
  )
}

function LayoutChat({ children, entrada }: { children: React.ReactNode; entrada?: React.ReactNode }) {
  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col px-4 pb-4">
      <Conversation className="flex-1">
        <ConversationContent className="gap-6 py-6">{children}</ConversationContent>
        <ConversationScrollButton />
      </Conversation>
      {entrada}
    </div>
  )
}

function Entrada({
  status,
  onEnviar,
  onParar,
}: {
  status: ChatStatus
  onEnviar: (texto: string) => void
  onParar?: () => void
}) {
  return (
    <PromptInput onSubmit={({ text }: PromptInputMessage) => onEnviar(text)}>
      <PromptInputBody>
        <PromptInputTextarea placeholder="Digite sua mensagem..." aria-label="Mensagem" />
      </PromptInputBody>
      <PromptInputFooter>
        <span className="px-2 text-xs text-muted-foreground">Enter envia, Shift+Enter quebra linha</span>
        <PromptInputSubmit
          status={status}
          onStop={onParar}
          aria-label={status === 'streaming' || status === 'submitted' ? 'Parar' : 'Enviar'}
        />
      </PromptInputFooter>
    </PromptInput>
  )
}

function TelaVazia({ onEscolher }: { onEscolher: (texto: string) => void }) {
  return (
    <div className="flex flex-1 flex-col items-center justify-center gap-6 py-16 text-center">
      <div className="flex size-12 items-center justify-center rounded-full bg-muted text-muted-foreground">
        <MessageSquareIcon className="size-6" />
      </div>
      <div className="space-y-1">
        <h1 className="text-xl font-semibold">Comece uma conversa</h1>
        <p className="text-sm text-muted-foreground">Escreva abaixo ou escolha uma sugestão.</p>
      </div>
      <div className="grid w-full max-w-xl gap-2">
        {SUGESTOES.map((s) => (
          <Button key={s} variant="outline" className="h-auto justify-start py-3 text-left font-normal whitespace-normal" onClick={() => onEscolher(s)}>
            {s}
          </Button>
        ))}
      </div>
    </div>
  )
}

function AvatarAssistente() {
  return <IconeApp className="size-8 rounded-full" />
}

function LinhaMensagem({ mensagem, quando, email }: { mensagem: UIMessage; quando?: Date; email?: string }) {
  const usuario = mensagem.role === 'user'
  return (
    <div className={cn('flex gap-3', usuario && 'flex-row-reverse')}>
      {usuario ? (
        <Avatar>
          <AvatarFallback className="text-xs">{email ? iniciais(email) : 'EU'}</AvatarFallback>
        </Avatar>
      ) : (
        <AvatarAssistente />
      )}
      <Message from={mensagem.role} className="min-w-0 max-w-[85%]">
        <MessageContent>
          {mensagem.parts.map((p, i) =>
            p.type === 'text' ? <MessageResponse key={i}>{p.text}</MessageResponse> : null,
          )}
        </MessageContent>
        {quando && (
          <time dateTime={quando.toISOString()} className={cn('text-xs text-muted-foreground', usuario && 'text-right')}>
            {hora(quando)}
          </time>
        )}
      </Message>
    </div>
  )
}

function Pensando() {
  return (
    <div className="flex items-center gap-3" role="status" aria-label="Assistente pensando">
      <AvatarAssistente />
      <div className="flex items-center gap-1.5">
        <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.3s]" />
        <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground [animation-delay:-0.15s]" />
        <span className="size-1.5 animate-bounce rounded-full bg-muted-foreground" />
        <Shimmer as="span" className="ml-2 text-sm">
          Pensando...
        </Shimmer>
      </div>
    </div>
  )
}
