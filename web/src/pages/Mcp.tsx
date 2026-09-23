import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { useSearchParams } from 'react-router'
import {
  AlertCircleIcon,
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
  ATALHOS_OAUTH,
  cadastrarServidor,
  iniciarOAuth,
  listarServidores,
  removerServidor,
  textoErroOAuthMcp,
  type McpOAuth,
  type McpServidor,
} from '@/lib/mcp'

const fmtData = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' })

/** Leva o browser ao consentimento do servidor (redirect, não popup). Devolve a mensagem de erro, se houver. */
async function irParaOAuth(pedido: McpOAuth): Promise<string | null> {
  try {
    window.location.assign((await iniciarOAuth(pedido)).url)
    return null
  } catch (err) {
    return err instanceof ErroApi && typeof err.detail === 'string'
      ? err.detail
      : 'Não foi possível iniciar a conexão OAuth. Tente de novo.'
  }
}

/** Tela /mcp: cadastrar Servidor MCP por URL + header ou por OAuth, ver as tools, ligar/desligar e remover. */
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
    <div className="mx-auto h-full max-w-3xl space-y-6 overflow-y-auto px-4 py-8">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">Servidores MCP</h1>
        <p className="text-sm text-muted-foreground">
          Cadastre um servidor MCP (Streamable HTTP) e as tools dele ficam disponíveis nas suas conversas. Você liga e
          desliga cada tool no seletor da conversa.
        </p>
      </div>
      <FormNovo onCadastrado={(s) => setServidores((ss) => [...(ss ?? []), s])} />
      {erro ? (
        <EstadoErro mensagem="Não foi possível carregar os servidores MCP." onTentarDeNovo={carregar} />
      ) : !servidores ? (
        <EstadoCarregando />
      ) : servidores.length === 0 ? (
        <EstadoVazio
          titulo="Nenhum servidor MCP ainda"
          descricao="Adicione a URL de um servidor acima. Ex.: o servidor remoto do GitHub com um token pessoal."
        />
      ) : (
        <div className="space-y-4">
          {servidores.map((s) => (
            <CardServidor key={s.id} s={s} onAlternar={alternar} onRemover={setRemovendo} onReconectar={reconectar} />
          ))}
        </div>
      )}
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

function FormNovo({ onCadastrado }: { onCadastrado: (s: McpServidor) => void }) {
  const [nome, setNome] = useState('')
  const [url, setUrl] = useState('')
  const [autorizacao, setAutorizacao] = useState('')
  const [enviando, setEnviando] = useState(false)
  const [indo, setIndo] = useState<string | null>(null) // nome do fluxo OAuth em andamento
  const [erro, setErro] = useState<string | null>(null)

  async function oauth(pedido: McpOAuth) {
    setIndo(pedido.nome)
    setErro(null)
    const falha = await irParaOAuth(pedido)
    if (falha) {
      setErro(falha)
      setIndo(null)
    }
  }

  async function enviar(e: FormEvent) {
    e.preventDefault()
    setEnviando(true)
    setErro(null)
    try {
      const s = await cadastrarServidor({ nome: nome.trim(), url: url.trim(), autorizacao: autorizacao.trim() || null })
      onCadastrado(s)
      toast.success(`${s.nome} conectado: ${s.tools.length} tools.`)
      setNome('')
      setUrl('')
      setAutorizacao('')
    } catch (err) {
      if (err instanceof ErroApi && err.status === 422) setErro('A URL precisa começar com http:// ou https://.')
      else setErro(err instanceof ErroApi && typeof err.detail === 'string' ? err.detail : 'Não foi possível cadastrar. Tente de novo.')
    } finally {
      setEnviando(false)
    }
  }

  return (
    <Card>
      <form onSubmit={enviar}>
        <CardHeader>
          <CardTitle className="text-base">Adicionar servidor</CardTitle>
          <CardDescription>
            Com header, o app conecta, lista as tools e só grava se a conexão der certo. Por OAuth, você autoriza na
            página do servidor e volta para cá.
          </CardDescription>
        </CardHeader>
        <CardContent className="flex flex-wrap items-center gap-2 pt-4">
          <span className="text-sm text-muted-foreground">Conectar em 1 clique:</span>
          {ATALHOS_OAUTH.map((a) => (
            <Button key={a.nome} type="button" variant="outline" size="sm" disabled={!!indo} onClick={() => void oauth(a)}>
              {indo === a.nome ? <Spinner /> : <ShieldCheckIcon />} {a.nome}
            </Button>
          ))}
        </CardContent>
        <CardContent className="grid gap-4 pt-4 pb-2 sm:grid-cols-[1fr_2fr]">
          <div className="space-y-2">
            <Label htmlFor="mcp-nome">Nome</Label>
            <Input id="mcp-nome" value={nome} onChange={(e) => setNome(e.target.value)} placeholder="GitHub" required maxLength={60} />
          </div>
          <div className="space-y-2">
            <Label htmlFor="mcp-url">URL</Label>
            <Input
              id="mcp-url"
              value={url}
              onChange={(e) => setUrl(e.target.value)}
              placeholder="https://api.githubcopilot.com/mcp/"
              required
              className="font-mono"
            />
          </div>
          <div className="space-y-2 sm:col-span-2">
            <Label htmlFor="mcp-auth">Header Authorization (opcional)</Label>
            <Input
              id="mcp-auth"
              type="password"
              autoComplete="off"
              value={autorizacao}
              onChange={(e) => setAutorizacao(e.target.value)}
              placeholder="Token solto vira Bearer. Ex.: ghp_... ou Bearer ..."
            />
            <p className="text-xs text-muted-foreground">Guardado cifrado. Nunca volta para a tela.</p>
          </div>
          {erro && (
            <p role="alert" className="flex items-start gap-2 text-sm text-destructive sm:col-span-2">
              <AlertCircleIcon className="mt-0.5 size-4 shrink-0" /> <span className="break-words">{erro}</span>
            </p>
          )}
        </CardContent>
        <CardFooter className="flex-wrap justify-end gap-2 pt-4">
          <Button
            type="button"
            variant="outline"
            disabled={enviando || !!indo || !nome.trim() || !url.trim()}
            onClick={() => void oauth({ nome: nome.trim(), url: url.trim() })}
          >
            {indo === nome.trim() ? <Spinner /> : <ShieldCheckIcon />} Conectar por OAuth
          </Button>
          <Button type="submit" disabled={enviando || !!indo || !nome.trim() || !url.trim()}>
            {enviando ? <Spinner /> : <PlugIcon />} {enviando ? 'Conectando...' : 'Conectar e listar tools'}
          </Button>
        </CardFooter>
      </form>
    </Card>
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
