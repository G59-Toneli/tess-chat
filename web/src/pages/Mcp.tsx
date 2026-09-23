import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router'
import {
  AlertCircleIcon,
  CheckIcon,
  ChevronDownIcon,
  ClockIcon,
  KeyRoundIcon,
  PlugIcon,
  RefreshCwIcon,
  ServerIcon,
  ShieldCheckIcon,
  Trash2Icon,
  TriangleAlertIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import { EstadoCarregando, EstadoErro, EstadoVazio } from '@/components/estados'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Spinner } from '@/components/ui/spinner'
import { Switch } from '@/components/ui/switch'
import { ErroApi } from '@/lib/api'
import {
  alternarServidor,
  CATALOGO_MCP,
  cadastrarServidor,
  iniciarOAuth,
  listarServidores,
  nomeDoHost,
  nomeLivre,
  removerServidor,
  textoErroOAuthMcp,
  type McpOAuth,
  type McpServidor,
} from '@/lib/mcp'

const fmtData = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' })

/** Texto do erro da API: string do back, ou fallback. 422 sem string é a URL fora do padrão http(s). */
function textoErro(err: unknown, fallback: string): string {
  if (err instanceof ErroApi && typeof err.detail === 'string') return err.detail
  if (err instanceof ErroApi && err.status === 422) return 'A URL precisa começar com http:// ou https://.'
  return fallback
}

/** Leva o browser ao consentimento do servidor (redirect, não popup). Devolve a mensagem de erro, se houver. */
async function irParaOAuth(pedido: McpOAuth): Promise<string | null> {
  try {
    const r = await iniciarOAuth(pedido)
    if (r.modo !== 'oauth') return 'Esse servidor não oferece login automático.'
    window.location.assign(r.url)
    return null
  } catch (err) {
    return textoErro(err, 'Não foi possível iniciar a conexão OAuth. Tente de novo.')
  }
}

/** Tela /mcp: catálogo de 1 clique, outro servidor por URL (o app detecta a auth) e os servidores do Usuário. */
export function Mcp() {
  const [servidores, setServidores] = useState<McpServidor[] | null>(null)
  const [erro, setErro] = useState(false)
  const [removendo, setRemovendo] = useState<McpServidor | null>(null)
  const [params, setParams] = useSearchParams()

  const carregar = useCallback(async () => {
    setErro(false)
    try {
      setServidores(await listarServidores())
    } catch {
      setErro(true)
    }
  }, [])

  useEffect(() => {
    void carregar()
  }, [carregar])

  // Volta do consentimento OAuth: avisa e limpa a query.
  useEffect(() => {
    const codigo = params.get('erro')
    if (params.get('conectado')) toast.success('Servidor MCP conectado por OAuth. As tools já estão nas suas conversas.', { id: 'oauth' })
    else if (codigo) toast.error(textoErroOAuthMcp(codigo), { id: 'oauth' })
    else return
    setParams({}, { replace: true })
  }, [params, setParams])

  const nomes = servidores?.map((s) => s.nome) ?? []

  async function reconectar(s: McpServidor) {
    const erro = await irParaOAuth({ nome: s.nome, url: s.url, sid: s.id })
    if (erro) toast.error(erro)
  }

  async function alternar(s: McpServidor, ativo: boolean) {
    setServidores((ss) => ss?.map((x) => (x.id === s.id ? { ...x, ativo } : x)) ?? ss)
    try {
      const novo = await alternarServidor(s.id, ativo)
      setServidores((ss) => ss?.map((x) => (x.id === s.id ? novo : x)) ?? ss)
      toast.success(ativo ? `${s.nome} ligado: as tools voltam às conversas.` : `${s.nome} desligado: as tools saem das conversas.`)
    } catch {
      toast.error('Não foi possível alterar o servidor. Tente de novo.')
      void carregar()
    }
  }

  async function remover(s: McpServidor) {
    try {
      await removerServidor(s.id)
      setServidores((ss) => ss?.filter((x) => x.id !== s.id) ?? ss)
      toast.success(`Servidor ${s.nome} removido.`)
    } catch {
      toast.error('Não foi possível remover o servidor. Tente de novo.')
    }
  }

  return (
    <div className="mx-auto h-full max-w-3xl space-y-8 overflow-y-auto px-4 py-8">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">Servidores MCP</h1>
        <p className="text-sm text-muted-foreground">
          Conecte um servidor MCP (Streamable HTTP) e as tools dele ficam disponíveis nas suas conversas. Você liga e
          desliga cada tool no seletor da conversa.
        </p>
      </div>
      <Catalogo servidores={servidores} nomes={nomes} onReconectar={reconectar} />
      <OutroServidor nomes={nomes} onCadastrado={(s) => setServidores((ss) => [...(ss ?? []), s])} />
      <section className="space-y-3">
        <h2 className="text-sm font-medium text-muted-foreground">Meus servidores</h2>
        {erro ? (
          <EstadoErro mensagem="Não foi possível carregar os servidores MCP." onTentarDeNovo={carregar} />
        ) : !servidores ? (
          <EstadoCarregando />
        ) : servidores.length === 0 ? (
          <EstadoVazio
            titulo="Nenhum servidor MCP ainda"
            descricao="Conecte um servidor do catálogo ou cole a URL de outro acima."
          />
        ) : (
          <div className="space-y-4">
            {servidores.map((s) => (
              <CardServidor key={s.id} s={s} onAlternar={alternar} onRemover={setRemovendo} onReconectar={reconectar} />
            ))}
          </div>
        )}
      </section>
      <AlertDialog open={!!removendo} onOpenChange={(v) => !v && setRemovendo(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remover {removendo?.nome}?</AlertDialogTitle>
            <AlertDialogDescription>
              As {removendo?.tools.length} tools deste servidor somem de todas as suas conversas. O header de
              autenticação guardado é apagado.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={() => removendo && void remover(removendo)}>
              Remover
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

// Logos em SVG inline, sem dependência nova. Formas simplificadas, não os arquivos oficiais.
function Logo({ nome }: { nome: string }) {
  if (nome === 'Notion')
    return (
      <svg viewBox="0 0 40 40" className="size-10 shrink-0" aria-hidden>
        <rect width="40" height="40" rx="8" fill="#fff" />
        <path d="M12 11h4l9 13V11h3v18h-4l-9-13v13h-3z" fill="#191919" />
      </svg>
    )
  return (
    <svg viewBox="0 0 40 40" className="size-10 shrink-0" aria-hidden>
      <rect width="40" height="40" rx="8" fill="#635BFF" />
      <path
        d="M19 16.4c0-1 .8-1.4 2.2-1.4 2 0 4.4.6 6.4 1.7v-6A17 17 0 0 0 21.2 9.5c-5.2 0-8.7 2.7-8.7 7.3 0 7.1 9.8 6 9.8 9 0 1.2-1 1.6-2.4 1.6-2.1 0-4.8-.9-6.9-2v6.1c2.4 1 4.7 1.5 6.9 1.5 5.4 0 9-2.6 9-7.3 0-7.7-9.9-6.3-9.9-9.2z"
        fill="#fff"
      />
    </svg>
  )
}

function Catalogo({
  servidores,
  nomes,
  onReconectar,
}: {
  servidores: McpServidor[] | null
  nomes: string[]
  onReconectar: (s: McpServidor) => Promise<void>
}) {
  const [indo, setIndo] = useState<string | null>(null) // item com fluxo OAuth em andamento

  async function conectar(nome: string, url: string, s: McpServidor | undefined) {
    setIndo(nome)
    if (s) await onReconectar(s)
    else {
      const erro = await irParaOAuth({ nome: nomeLivre(nome, nomes), url })
      if (erro) toast.error(erro)
    }
    setIndo(null) // com redirect, a página já saiu antes de o spinner parar
  }

  return (
    <section className="space-y-3">
      <h2 className="text-sm font-medium text-muted-foreground">Conectar em 1 clique</h2>
      <div className="grid gap-4 sm:grid-cols-2">
        {CATALOGO_MCP.map((a) => {
          const s = servidores?.find((x) => x.url === a.url)
          return (
            <Card key={a.nome} className="py-4">
              <CardContent className="flex items-center gap-3 px-4">
                <Logo nome={a.nome} />
                <div className="min-w-0 flex-1">
                  <p className="font-medium">{a.nome}</p>
                  <p className="text-sm text-muted-foreground">{a.descricao}</p>
                </div>
                {s?.estado === 'ok' ? (
                  <Button size="sm" variant="secondary" disabled className="disabled:opacity-100">
                    <CheckIcon className="text-emerald-500" /> Conectado
                  </Button>
                ) : (
                  <Button
                    size="sm"
                    variant={s ? 'default' : 'outline'}
                    disabled={!servidores || !!indo}
                    onClick={() => void conectar(a.nome, a.url, s)}
                  >
                    {indo === a.nome ? <Spinner /> : s ? <RefreshCwIcon /> : <PlugIcon />} {s ? 'Reconectar' : 'Conectar'}
                  </Button>
                )}
              </CardContent>
            </Card>
          )
        })}
      </div>
    </section>
  )
}

// REVISAR(human): o usuário só cola a URL. O iniciar detecta o caminho: oauth vai ao consentimento,
// sem_auth cadastra direto pelo POST sem header, token expande o campo. Mudar a URL volta ao passo 1.
function OutroServidor({ nomes, onCadastrado }: { nomes: string[]; onCadastrado: (s: McpServidor) => void }) {
  const [url, setUrl] = useState('')
  const [pedeToken, setPedeToken] = useState(false)
  const [nome, setNome] = useState('')
  const [token, setToken] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [erro, setErro] = useState<string | null>(null)

  async function cadastrar(nomeFinal: string, autorizacao: string | null) {
    const s = await cadastrarServidor({ nome: nomeFinal, url: url.trim(), autorizacao })
    onCadastrado(s)
    toast.success(`${s.nome} conectado: ${s.tools.length} tools.`)
    setUrl('')
    setPedeToken(false)
    setNome('')
    setToken('')
  }

  async function enviar(e: FormEvent) {
    e.preventDefault()
    setEnviando(true)
    setErro(null)
    try {
      if (pedeToken) await cadastrar(nome.trim(), token.trim())
      else {
        const sugerido = nomeLivre(nomeDoHost(url.trim()).slice(0, 60), nomes)
        const r = await iniciarOAuth({ nome: sugerido, url: url.trim() })
        if (r.modo === 'oauth') {
          window.location.assign(r.url)
          return // o botão segue girando até o browser sair da página
        }
        if (r.modo === 'sem_auth') await cadastrar(sugerido, null)
        else {
          setNome(sugerido)
          setPedeToken(true)
        }
      }
    } catch (err) {
      setErro(textoErro(err, 'Não foi possível conectar. Tente de novo.'))
    }
    setEnviando(false)
  }

  const pronto = !!url.trim() && (!pedeToken || (!!nome.trim() && !!token.trim()))

  return (
    <section className="space-y-3">
      <h2 className="text-sm font-medium text-muted-foreground">Outro servidor</h2>
      <Card>
        <form onSubmit={enviar}>
          <CardContent className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="mcp-url">URL do servidor</Label>
              <div className="flex gap-2">
                <Input
                  id="mcp-url"
                  value={url}
                  onChange={(e) => {
                    setUrl(e.target.value)
                    setPedeToken(false)
                    setErro(null)
                  }}
                  placeholder="https://mcp.linear.app/mcp"
                  required
                  className="font-mono"
                />
                {!pedeToken && (
                  <Button type="submit" disabled={enviando || !pronto}>
                    {enviando ? <Spinner /> : <PlugIcon />} Conectar
                  </Button>
                )}
              </div>
              {!pedeToken && (
                <p className="text-xs text-muted-foreground">
                  O app descobre sozinho se o servidor tem login automático (OAuth), se é aberto ou se pede token.
                </p>
              )}
            </div>
            {pedeToken && (
              <div className="space-y-4 rounded-lg border bg-muted/30 p-4">
                <p className="flex items-start gap-2 text-sm">
                  <KeyRoundIcon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                  Esse servidor não oferece login automático. Cole um token de acesso dele.
                </p>
                <div className="grid gap-4 sm:grid-cols-[1fr_2fr]">
                  <div className="space-y-2">
                    <Label htmlFor="mcp-nome">Nome</Label>
                    <Input id="mcp-nome" value={nome} onChange={(e) => setNome(e.target.value)} required maxLength={60} />
                  </div>
                  <div className="space-y-2">
                    <Label htmlFor="mcp-auth">Token de acesso</Label>
                    <Input
                      id="mcp-auth"
                      type="password"
                      autoComplete="off"
                      autoFocus
                      value={token}
                      onChange={(e) => setToken(e.target.value)}
                      placeholder="Token solto vira Bearer. Ex.: ghp_... ou Bearer ..."
                      required
                    />
                  </div>
                </div>
                <div className="flex flex-wrap items-center justify-between gap-2">
                  <p className="text-xs text-muted-foreground">Guardado cifrado. Nunca volta para a tela.</p>
                  <Button type="submit" disabled={enviando || !pronto}>
                    {enviando ? <Spinner /> : <PlugIcon />} {enviando ? 'Conectando...' : 'Conectar e listar tools'}
                  </Button>
                </div>
              </div>
            )}
            {erro && (
              <p role="alert" className="flex items-start gap-2 text-sm text-destructive">
                <AlertCircleIcon className="mt-0.5 size-4 shrink-0" /> <span className="break-words">{erro}</span>
              </p>
            )}
          </CardContent>
        </form>
      </Card>
    </section>
  )
}

function CardServidor({
  s,
  onAlternar,
  onRemover,
  onReconectar,
}: {
  s: McpServidor
  onAlternar: (s: McpServidor, ativo: boolean) => void
  onRemover: (s: McpServidor) => void
  onReconectar: (s: McpServidor) => void
}) {
  const id = `mcp-ativo-${s.id}`
  const pendente = s.estado !== 'ok'
  return (
    <Card className={s.ativo ? undefined : 'opacity-70'}>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2 text-base">
          <ServerIcon className="size-4 text-muted-foreground" /> {s.nome}
          <Badge variant="secondary">{s.tools.length} tools</Badge>
          {s.oauth ? (
            <Badge variant="outline" className="font-normal">
              <ShieldCheckIcon /> OAuth
            </Badge>
          ) : (
            s.tem_auth && (
              <Badge variant="outline" className="font-normal">
                <KeyRoundIcon /> com autenticação
              </Badge>
            )
          )}
          {s.estado === 'aguardando_oauth' && (
            <Badge variant="secondary" className="font-normal">
              <ClockIcon /> aguardando autorização
            </Badge>
          )}
          {s.estado === 'expirado' && (
            <Badge variant="destructive" className="font-normal">
              <TriangleAlertIcon /> conexão expirada
            </Badge>
          )}
          <div className="ml-auto flex items-center gap-2">
            <Label htmlFor={id} className="text-sm font-normal text-muted-foreground">
              {s.ativo ? 'Ligado' : 'Desligado'}
            </Label>
            <Switch id={id} checked={s.ativo} disabled={pendente} onCheckedChange={(v) => onAlternar(s, v)} />
          </div>
        </CardTitle>
        <CardDescription className="truncate font-mono text-xs" title={s.url}>
          {s.url}
        </CardDescription>
      </CardHeader>
      <CardContent className="space-y-2 pt-2">
        {pendente && (
          <p className="flex items-start gap-2 text-sm text-muted-foreground">
            <AlertCircleIcon className="mt-0.5 size-4 shrink-0" />
            {s.estado === 'expirado'
              ? 'A autorização venceu e não pôde ser renovada. As tools ficam fora das conversas até você reconectar.'
              : 'A autorização não foi concluída. Reconecte para liberar as tools.'}
          </p>
        )}
        <Collapsible>
          <CollapsibleTrigger asChild>
            <Button variant="ghost" size="sm" className="group -ml-2 text-muted-foreground">
              <ChevronDownIcon className="transition-transform group-data-[state=open]:rotate-180" /> Ver tools
            </Button>
          </CollapsibleTrigger>
          <CollapsibleContent>
            <ul className="mt-2 max-h-72 space-y-3 overflow-y-auto border-l pl-4">
              {s.tools.map((t) => (
                <li key={t.nome} className="space-y-0.5">
                  <p className="font-mono text-sm break-all">{t.nome}</p>
                  <p className="line-clamp-2 text-xs text-muted-foreground">{t.descricao}</p>
                </li>
              ))}
            </ul>
          </CollapsibleContent>
        </Collapsible>
      </CardContent>
      <CardFooter className="justify-between pt-2 text-xs text-muted-foreground">
        <span>Adicionado em {fmtData.format(new Date(s.created_at))}</span>
        <div className="flex gap-2">
          {s.oauth && pendente && (
            <Button size="sm" onClick={() => onReconectar(s)}>
              <RefreshCwIcon /> Reconectar
            </Button>
          )}
          <Button variant="outline" size="sm" onClick={() => onRemover(s)}>
            <Trash2Icon /> Remover
          </Button>
        </div>
      </CardFooter>
    </Card>
  )
}
