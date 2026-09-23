import { useCallback, useEffect, useMemo, useRef, useState } from 'react'
import { Link, useNavigate, useParams } from 'react-router'
import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport, type ChatStatus, type FileUIPart, type UIMessage } from 'ai'
import { toast } from 'sonner'
import { MessageSquareIcon, OctagonPauseIcon, WalletIcon } from 'lucide-react'
import { BadgeUso, BlocoTool, Buscando, LinhaRoteador, nomeDaTool, partesDeTool, toolRodando, useDuracoes } from '@/components/BlocoTool'
import { AnexoNaMensagem, AnexosDoPrompt, BotaoAnexar, previews } from '@/components/Anexos'
import { SeletorTools } from '@/components/SeletorTools'
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
import {
  ACEITOS,
  LIMITE_ANEXO,
  authHeader,
  criarConversa,
  enviarAnexo,
  listarMensagens,
  sair,
  textoErroAnexo,
  textoErroChat,
} from '@/lib/api'
import { hora, iniciais } from '@/lib/datas'
import { decisoesDoRoteador, ehErroDeCap, usoPorMensagem, type MensagemComUso, type Uso } from '@/lib/tools'
import { cn } from '@/lib/utils'

const SUGESTOES = [
  'Explique o que é um LLM em três frases.',
  'Me dê ideias de nome para um app de tarefas.',
  'Escreva um e-mail curto pedindo reunião na sexta.',
]

// Texto e anexos enviados em "/" antes de a Conversa existir. O chat da nova rota consome uma vez.
const pendentes = new Map<string, { texto: string; arquivos: FileUIPart[] }>()

/** Sobe os anexos e devolve as partes que vão na Mensagem, com a URL da API. Falha: toast e lança. */
async function subirAnexos(arquivos: FileUIPart[]): Promise<FileUIPart[]> {
  try {
    return await Promise.all(
      arquivos.map(async (f) => {
        const a = await enviarAnexo(f.url, f.filename ?? 'anexo')
        previews.set(a.url, f.url)
        return { type: 'file' as const, url: a.url, mediaType: a.mime_type, filename: a.filename }
      }),
    )
  } catch (e) {
    toast.error(textoErroAnexo(e))
    throw e
  }
}

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

  async function comecar(texto: string, arquivos: FileUIPart[] = []) {
    if ((!texto.trim() && arquivos.length === 0) || criando) return
    setCriando(true)
    let partes: FileUIPart[]
    try {
      partes = await subirAnexos(arquivos)
    } catch (e) {
      setCriando(false)
      throw e
    }
    try {
      const conv = await criarConversa(tituloDe(texto) || (arquivos[0]?.filename ?? 'Anexo'))
      pendentes.set(conv.id, { texto, arquivos: partes })
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
  const [inicial, setInicial] = useState<{
    mensagens: UIMessage[]
    horarios: Map<string, Date>
    usos: Map<string, Uso>
  } | null>(null)
  const [erro, setErro] = useState(false)

  const carregar = useCallback(async () => {
    setErro(false)
    try {
      const [linhas, decisoes] = await Promise.all([
        listarMensagens(id) as Promise<MensagemComUso[]>,
        decisoesDoRoteador(id).catch(() => []),
      ])
      const visiveis = linhas.filter((m) => m.role === 'user' || m.role === 'assistant')
      // Um turno com tool vira várias linhas assistant seguidas. Junto numa só, como no stream.
      // Fica o id da última linha: é ela que tem o uso.
      const mensagens: UIMessage[] = []
      for (const m of visiveis) {
        const anterior = mensagens.at(-1)
        const parts = m.parts as UIMessage['parts']
        if (m.role === 'assistant' && anterior?.role === 'assistant')
          mensagens[mensagens.length - 1] = { ...anterior, id: String(m.id), parts: [...anterior.parts, ...parts] }
        else mensagens.push({ id: String(m.id), role: m.role as 'user' | 'assistant', parts })
      }
      setInicial({
        usos: usoPorMensagem(linhas, decisoes),
        mensagens,
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
  return <ChatConversa id={id} inicial={inicial.mensagens} horarios={inicial.horarios} usosIniciais={inicial.usos} />
}

function ChatConversa({
  id,
  inicial,
  horarios,
  usosIniciais,
}: {
  id: string
  inicial: UIMessage[]
  horarios: Map<string, Date>
  usosIniciais: Map<string, Uso>
}) {
  const { usuario, recarregarConversas } = useContextoApp()
  const [usos, setUsos] = useState(usosIniciais)

  // O stream não traz usage nem a decisão do Roteador. A API grava os dois antes do fim
  // do stream, então no onFinish a última resposta do banco já é a deste turno.
  const buscarUso = useCallback(
    async (mensagemId: string) => {
      try {
        const [linhas, decisoes] = await Promise.all([
          listarMensagens(id) as Promise<MensagemComUso[]>,
          decisoesDoRoteador(id).catch(() => []),
        ])
        const ultima = linhas.filter((m) => m.role === 'assistant').at(-1)
        const uso = ultima && usoPorMensagem(linhas, decisoes).get(String(ultima.id))
        if (uso) setUsos((u) => new Map(u).set(mensagemId, uso))
      } catch {
        // Badge é informativo: sem ele a resposta continua visível.
      }
    },
    [id],
  )
  const transport = useMemo(
    // headers como função: lê o token na hora do envio.
    () => new DefaultChatTransport({ api: `/api/chat/${id}`, headers: () => authHeader() }),
    [id],
  )
  const { messages, sendMessage, status, stop, error, regenerate, clearError } = useChat({
    id,
    messages: inicial,
    transport,
    onFinish: ({ message, isError, isAbort }) => {
      void recarregarConversas()
      if (!isError && !isAbort) void buscarUso(message.id)
    },
  })
  const duracoes = useDuracoes(messages)
  const cap = !!error && ehErroDeCap(error as Error & { statusCode?: number })

  // Envia o texto que veio de "/". O setTimeout sobrevive ao StrictMode: o cleanup do
  // useChat chama stop() e abortaria um envio feito direto no primeiro efeito.
  useEffect(() => {
    const pendente = pendentes.get(id)
    if (pendente === undefined) return
    const t = setTimeout(() => {
      pendentes.delete(id)
      void sendMessage({ text: pendente.texto, files: pendente.arquivos })
    })
    return () => clearTimeout(t)
  }, [id, sendMessage])

  useEffect(() => {
    if (!error) return
    const e = error as Error & { statusCode?: number }
    if (e.statusCode === 401) return sair()
    if (ehErroDeCap(e)) return // Mensagem própria no fim da conversa, não toast.
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
  // Resposta só com tool (ainda sem texto) aparece: o bloco de tool é o progresso do turno.
  const vazia = (m?: UIMessage) => semTexto(m) && (!m || partesDeTool(m).length === 0)
  const pensando = status === 'submitted' || (status === 'streaming' && ultima?.role === 'assistant' && vazia(ultima))
  const visiveis = messages.filter((m) => m.role === 'user' || !vazia(m))

  async function enviar(texto: string, arquivos: FileUIPart[] = []) {
    if ((!texto.trim() && arquivos.length === 0) || status === 'submitted' || status === 'streaming') return
    const partes = await subirAnexos(arquivos)
    if (error) clearError()
    void sendMessage({ text: texto, files: partes })
  }

  return (
    <LayoutChat
      entrada={<Entrada conversaId={id} status={status} onEnviar={enviar} onParar={stop} />}
    >
      {visiveis.length === 0 && !pensando && !cap ? (
        <TelaVazia onEscolher={enviar} />
      ) : (
        <>
          {visiveis.map((m) => (
            <MarcadorCompactacao key={m.id} conversaId={id} mensagemId={m.id}><LinhaMensagem
              key={m.id}
              mensagem={m}
              quando={hs.current.get(m.id)}
              email={usuario?.email}
              uso={usos.get(m.id)}
              duracoes={duracoes}
            /></MarcadorCompactacao>
          ))}
          {pensando && <Pensando />}
          {cap && <AvisoCap />}
        </>
      )}
    </LayoutChat>
  )
}

function LayoutChat({
  children,
  entrada,
}: {
  children: React.ReactNode
  entrada?: React.ReactNode
}) {
  return (
    <div className="flex h-full">
      <div className="mx-auto flex h-full min-w-0 max-w-3xl flex-1 flex-col px-4 pb-4">
        <Conversation className="flex-1">
          <ConversationContent className="gap-6 py-6">{children}</ConversationContent>
          <ConversationScrollButton />
        </Conversation>
        {entrada}
      </div>
    </div>
  )
}

function AvisoCap() {
  return (
    <div role="alert" className="flex items-start gap-3 rounded-lg border border-destructive/40 bg-destructive/10 p-4">
      <WalletIcon className="mt-0.5 size-5 shrink-0 text-destructive" />
      <div className="flex-1 space-y-1">
        <p className="text-sm font-medium">Seu limite de crédito acabou</p>
        <p className="text-sm text-muted-foreground">
          A mensagem não foi enviada ao modelo. Veja o saldo e o limite em Créditos.
        </p>
      </div>
      <Button asChild size="sm">
        <Link to="/creditos">Ver créditos</Link>
      </Button>
    </div>
  )
}

function Entrada({
  conversaId,
  status,
  onEnviar,
  onParar,
}: {
  conversaId?: string
  status: ChatStatus
  onEnviar: (texto: string, arquivos: FileUIPart[]) => Promise<void>
  onParar?: () => void
}) {
  return (
    <PromptInput
      onSubmit={({ text, files }: PromptInputMessage) => onEnviar(text, files)}
      accept={ACEITOS}
      multiple
      maxFileSize={LIMITE_ANEXO}
      onError={({ code }) =>
        toast.error(code === 'max_file_size' ? 'Arquivo acima de 20 MB.' : 'Tipo não permitido. Envie PNG, JPG, WEBP ou PDF.')
      }
    >
      <AnexosDoPrompt />
      <PromptInputBody>
        <PromptInputTextarea placeholder="Digite sua mensagem..." aria-label="Mensagem" autoFocus />
      </PromptInputBody>
      <PromptInputFooter>
        <div className="flex items-center gap-1">
          <BotaoAnexar />
          <SeletorTools conversaId={conversaId} />
          <span className="px-1 text-xs text-muted-foreground">Enter envia, Shift+Enter quebra linha</span>
        </div>
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

function LinhaMensagem({
  mensagem,
  quando,
  email,
  uso,
  duracoes,
}: {
  mensagem: UIMessage
  quando?: Date
  email?: string
  uso?: Uso
  duracoes?: Map<string, number>
}) {
  const usuario = mensagem.role === 'user'
  const tools = partesDeTool(mensagem)
  const primeiraTool = tools[0]
  const corte = interrupcaoDa(mensagem)
  const interrompidas = new Set(corte?.tool_call_ids ?? [])
  const rodando = toolRodando(mensagem) ? tools.find((p) => p.state !== 'output-available') : undefined
  // Só decisão que forçou a Tool. Abaixo do limiar quem decidiu foi o Gemini.
  const decisao = uso?.decisao?.forcada ? uso.decisao : undefined
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
          {mensagem.parts.map((p, i) => {
            if (p.type === 'text') return <MessageResponse key={i}>{p.text}</MessageResponse>
            if (p.type === 'file') return <AnexoNaMensagem key={i} parte={p} />
            const parte = tools.find((t) => t === p)
            if (!parte) return null
            return (
              <div key={i} className="space-y-1.5">
                {decisao && parte === primeiraTool && <LinhaRoteador decisao={decisao} />}
                <BlocoTool
                  parte={parte}
                  duracaoMs={duracoes?.get(parte.toolCallId)}
                  interrompida={interrompidas.has(parte.toolCallId)}
                />
              </div>
            )
          })}
          {rodando && !corte && <Buscando nome={nomeDaTool(rodando)} />}
          {corte && <AvisoTurnoInterrompido corte={corte} />}
        </MessageContent>
        {(quando || uso) && (
          <div className={cn('flex flex-wrap items-center gap-x-3 gap-y-1', usuario && 'justify-end')}>
            {quando && (
              <time dateTime={quando.toISOString()} className="text-xs text-muted-foreground">
                {hora(quando)}
              </time>
            )}
            {uso && !usuario && <BadgeUso uso={uso} />}
          </div>
        )}
      </Message>
    </div>
  )
}

// Part que a API grava quando corta o turno (ticket 30): teto de tools ou servidor MCP que caiu.
type Interrupcao = { texto: string; motivo: string; tool_call_ids?: string[] }

function interrupcaoDa(m: UIMessage): Interrupcao | undefined {
  const p = m.parts.find((x) => x.type === 'data-turno-interrompido')
  return p && 'data' in p ? (p.data as Interrupcao) : undefined
}

function AvisoTurnoInterrompido({ corte }: { corte: Interrupcao }) {
  return (
    <div role="status" className="flex items-start gap-3 rounded-lg border bg-muted/40 p-3">
      <OctagonPauseIcon className="mt-0.5 size-4 shrink-0 text-amber-500" />
      <p className="text-sm">
        {corte.texto}
        {corte.motivo === 'tool_limit_reached' && (
          <>
            {' '}Você pode aumentar o limite em{' '}
            <Link to="/config" className="font-medium underline underline-offset-4">
              Configuração
            </Link>
            .
          </>
        )}
      </p>
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
