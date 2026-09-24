import { useCallback, useEffect, useMemo, useRef, useState, type ReactNode } from 'react'
import {
  AlertCircleIcon,
  CheckCircle2Icon,
  FlaskConicalIcon,
  GlobeIcon,
  SaveIcon,
  Trash2Icon,
  WandSparklesIcon,
  XCircleIcon,
} from 'lucide-react'
import { toast } from 'sonner'
import { CodeBlock } from '@/components/ai-elements/code-block'
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
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Spinner } from '@/components/ui/spinner'
import { Switch } from '@/components/ui/switch'
import { Textarea } from '@/components/ui/textarea'
import { ErroApi } from '@/lib/api'
import {
  cadastrarApiTool,
  LIMITE_DESCRICAO,
  LIMITE_NOME,
  listarApiTools,
  listarModelos,
  nomeSugerido,
  placeholders,
  removerApiTool,
  rotuloModelo,
  testarApiTool,
  type ApiTool,
  type ApiToolNova,
  type Auth,
  type Metodo,
  type Parametro,
  type Teste,
  type TipoParametro,
} from '@/lib/apiTools'

const fmtData = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' })

const TIPOS: { valor: TipoParametro; rotulo: string }[] = [
  { valor: 'string', rotulo: 'Texto' },
  { valor: 'number', rotulo: 'Número' },
  { valor: 'integer', rotulo: 'Número inteiro' },
  { valor: 'boolean', rotulo: 'Sim ou não' },
]

type Detalhe = Omit<Parametro, 'nome'> & { exemplo: string }
const DETALHE_PADRAO: Detalhe = { tipo: 'string', descricao: '', obrigatorio: true, exemplo: '' }

/** Texto do erro da API: string do back, ou fallback. */
function textoErro(err: unknown, fallback: string): string {
  if (err instanceof ErroApi && typeof err.detail === 'string') return err.detail
  if (err instanceof ErroApi && err.status === 422) return 'Algum campo está fora do formato. Confira a URL e o nome.'
  return fallback
}

function host(url: string): string {
  try {
    return new URL(url.replace(/[{}]/g, '')).host
  } catch {
    return url
  }
}

/** Tela /api-tools: modelos prontos, cadastro guiado com teste e a lista de Tools por API do Usuário. */
export function ApiTools() {
  const [tools, setTools] = useState<ApiTool[] | null>(null)
  const [erro, setErro] = useState(false)
  const [removendo, setRemovendo] = useState<ApiTool | null>(null)
  const [modelo, setModelo] = useState<{ nova: ApiToolNova | null; n: number } | null>(null)
  const formRef = useRef<HTMLDivElement>(null)

  const carregar = useCallback(async () => {
    setErro(false)
    try {
      setTools(await listarApiTools())
    } catch {
      setErro(true)
    }
  }, [])

  useEffect(() => {
    void carregar()
  }, [carregar])

  function usar(nova: ApiToolNova) {
    setModelo((m) => ({ nova, n: (m?.n ?? 0) + 1 }))
    formRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' })
  }

  async function remover(t: ApiTool) {
    try {
      await removerApiTool(t.id)
      setTools((ts) => ts?.filter((x) => x.id !== t.id) ?? ts)
      toast.success(`Tool ${t.nome} removida.`)
    } catch {
      toast.error('Não foi possível remover a tool. Tente de novo.')
    }
  }

  return (
    <div className="mx-auto h-full max-w-3xl space-y-8 overflow-y-auto px-4 py-8">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">Tools por API</h1>
        <p className="text-sm text-muted-foreground">
          Transforme uma API HTTP numa tool que o assistente usa nas suas conversas. Sem código: preencha, teste e
          salve.
        </p>
      </div>
      <Modelos onUsar={usar} />
      <div ref={formRef} className="scroll-mt-4">
        {/* key: "Usar" remonta o formulário com o modelo, sem efeito para copiar props em estado. */}
        <Formulario
          key={modelo?.n ?? 0}
          inicial={modelo?.nova ?? null}
          onSalva={(t) => {
            setTools((ts) => [...(ts ?? []), t])
            setModelo((m) => ({ nova: null, n: (m?.n ?? 0) + 1 })) // remonta vazio
          }}
        />
      </div>
      <section className="space-y-3">
        <h2 className="text-sm font-medium text-muted-foreground">Minhas tools por API</h2>
        {erro ? (
          <EstadoErro mensagem="Não foi possível carregar as tools por API." onTentarDeNovo={carregar} />
        ) : !tools ? (
          <EstadoCarregando />
        ) : tools.length === 0 ? (
          <EstadoVazio titulo="Nenhuma tool por API ainda" descricao="Use um modelo ou preencha o formulário acima." />
        ) : (
          <div className="space-y-4">
            {tools.map((t) => (
              <CardApiTool key={t.id} t={t} onRemover={setRemovendo} />
            ))}
          </div>
        )}
      </section>
      <AlertDialog open={!!removendo} onOpenChange={(v) => !v && setRemovendo(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Remover {removendo?.nome}?</AlertDialogTitle>
            <AlertDialogDescription>
              A tool some de todas as suas conversas. O segredo de autenticação guardado é apagado.
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

function Modelos({ onUsar }: { onUsar: (m: ApiToolNova) => void }) {
  const [modelos, setModelos] = useState<ApiToolNova[] | null>(null)
  const [erro, setErro] = useState(false)

  const carregar = useCallback(async () => {
    setErro(false)
    try {
      setModelos(await listarModelos())
    } catch {
      setErro(true)
    }
  }, [])

  useEffect(() => {
    void carregar()
  }, [carregar])

  return (
    <section className="space-y-3">
      <h2 className="text-sm font-medium text-muted-foreground">Começar de um modelo</h2>
      {erro ? (
        <EstadoErro mensagem="Não foi possível carregar os modelos." onTentarDeNovo={carregar} />
      ) : !modelos ? (
        <EstadoCarregando />
      ) : (
        <div className="grid gap-4 md:grid-cols-3">
          {modelos.map((m) => (
            <Card key={m.nome} className="gap-3 py-4">
              <CardContent className="flex h-full flex-col gap-3 px-4">
                <div className="min-w-0 flex-1 space-y-1">
                  <p className="flex items-center gap-2 font-medium">
                    {rotuloModelo(m.nome)}
                    <Badge variant="outline" className="font-mono text-[10px]">
                      {m.metodo}
                    </Badge>
                  </p>
                  <p className="line-clamp-3 text-sm text-muted-foreground">{m.descricao}</p>
                </div>
                <Button size="sm" variant="outline" className="self-start" onClick={() => onUsar(m)}>
                  <WandSparklesIcon /> Usar
                </Button>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </section>
  )
}

function Passo({ n, titulo, children }: { n: number; titulo: string; children: ReactNode }) {
  return (
    <fieldset className="space-y-3">
      <legend className="mb-3 flex items-center gap-2 text-sm font-medium">
        <span className="flex size-5 items-center justify-center rounded-full bg-primary text-[11px] text-primary-foreground">
          {n}
        </span>
        {titulo}
      </legend>
      {children}
    </fieldset>
  )
}

function detalhesDe(m: ApiToolNova | null): Record<string, Detalhe> {
  if (!m) return {}
  return Object.fromEntries(
    m.parametros.map((p) => [
      p.nome,
      { tipo: p.tipo, descricao: p.descricao, obrigatorio: p.obrigatorio, exemplo: String(m.exemplo[p.nome] ?? '') },
    ]),
  )
}

// REVISAR(human): o formulário é a fonte do body. Os parâmetros saem dos {param} da URL e do corpo,
// na hora; o detalhe de cada um fica guardado pelo nome, então apagar e redigitar um placeholder
// não perde a descrição. O teste vale para a definição exata que rodou: guarda o JSON do body
// testado, e Salvar só liga se o body atual for igual e o status for 2xx. Mudar qualquer campo,
// inclusive o segredo, muda o JSON e desliga Salvar.
function Formulario({ inicial, onSalva }: { inicial: ApiToolNova | null; onSalva: (t: ApiTool) => void }) {
  const [metodo, setMetodo] = useState<Metodo>(inicial?.metodo ?? 'GET')
  const [url, setUrl] = useState(inicial?.url ?? '')
  const [detalhes, setDetalhes] = useState<Record<string, Detalhe>>(() => detalhesDe(inicial))
  const [auth, setAuth] = useState<Auth>(inicial?.auth ?? { tipo: 'nenhuma' })
  const [nome, setNome] = useState<string | null>(inicial?.nome ?? null) // null: segue a sugestão
  const [descricao, setDescricao] = useState(inicial?.descricao ?? '')
  const [corpoTexto, setCorpoTexto] = useState(inicial?.corpo != null ? JSON.stringify(inicial.corpo, null, 2) : '')
  const [teste, setTeste] = useState<{ chave: string; r: Teste } | null>(null)
  const [erroTeste, setErroTeste] = useState<{ chave: string; msg: string } | null>(null)
  const [testando, setTestando] = useState(false)
  const [salvando, setSalvando] = useState(false)
  const [erroSalvar, setErroSalvar] = useState<string | null>(null)

  const nomeFinal = nome ?? nomeSugerido(url)
  const post = metodo === 'POST'

  const corpo = useMemo((): { valor: unknown; erro: string | null } => {
    if (!post || !corpoTexto.trim()) return { valor: null, erro: null }
    try {
      return { valor: JSON.parse(corpoTexto), erro: null }
    } catch (e) {
      return { valor: null, erro: e instanceof Error ? e.message : 'JSON inválido.' }
    }
  }, [post, corpoTexto])

  const nomes = useMemo(() => {
    const semFragmento = url.split('#')[0].replace(/^https?:\/\/[^/?]*/, '')
    return [...new Set([...placeholders(semFragmento), ...(post ? placeholders(corpoTexto) : [])])]
  }, [url, post, corpoTexto])
  const parametros = nomes.map((n) => ({ nome: n, ...(detalhes[n] ?? DETALHE_PADRAO) }))

  const body: ApiToolNova = {
    nome: nomeFinal,
    descricao: descricao.trim(),
    metodo,
    url: url.trim(),
    parametros: parametros.map(({ exemplo: _, ...p }) => p),
    corpo: corpo.valor,
    auth:
      auth.tipo === 'header'
        ? { tipo: 'header', nome: auth.nome ?? '', valor: auth.valor ?? '' }
        : auth.tipo === 'bearer'
          ? { tipo: 'bearer', token: auth.token ?? '' }
          : { tipo: 'nenhuma' },
    exemplo: Object.fromEntries(parametros.filter((p) => p.exemplo.trim()).map((p) => [p.nome, p.exemplo.trim()])),
  }
  const chave = JSON.stringify(body)

  const pendencias = [
    !/^https?:\/\/\S+$/.test(body.url) && 'uma URL que comece com http:// ou https://',
    parametros.some((p) => !p.descricao.trim()) && 'a descrição de cada parâmetro',
    parametros.some((p) => p.obrigatorio && !p.exemplo.trim()) && 'um valor de exemplo em cada parâmetro obrigatório',
    auth.tipo === 'header' && !(auth.nome?.trim() && auth.valor) && 'o nome e o valor do header',
    auth.tipo === 'bearer' && !auth.token && 'o token',
    !/^[a-z][a-z0-9_]*$/.test(nomeFinal) && 'um nome com letras minúsculas, números e _',
    !body.descricao && 'a descrição da tool',
    corpo.erro && 'um corpo JSON válido',
  ].filter(Boolean) as string[]

  const testeAtual = teste?.chave === chave ? teste.r : null
  const ok = !!testeAtual && testeAtual.status >= 200 && testeAtual.status < 300

  function detalhe(n: string, mudanca: Partial<Detalhe>) {
    setDetalhes((d) => ({ ...d, [n]: { ...(d[n] ?? DETALHE_PADRAO), ...mudanca } }))
  }

  async function testar() {
    setTestando(true)
    setErroTeste(null)
    setErroSalvar(null)
    try {
      setTeste({ chave, r: await testarApiTool(body) })
    } catch (err) {
      setTeste(null)
      setErroTeste({ chave, msg: textoErro(err, 'Não foi possível testar. Tente de novo.') })
    }
    setTestando(false)
  }

  async function salvar() {
    setSalvando(true)
    setErroSalvar(null)
    try {
      const t = await cadastrarApiTool(body)
      onSalva(t)
      toast.success(`${t.nome} salva. Ela já aparece no botão de tools das suas conversas.`)
    } catch (err) {
      setErroSalvar(textoErro(err, 'Não foi possível salvar. Tente de novo.'))
      setSalvando(false)
    }
  }

  return (
    <section className="space-y-3">
      <h2 className="text-sm font-medium text-muted-foreground">
        {inicial ? `Nova tool a partir do modelo ${rotuloModelo(inicial.nome)}` : 'Nova tool'}
      </h2>
      <Card>
        <CardContent className="space-y-8">
          <Passo n={1} titulo="URL e método">
            <div className="flex gap-2">
              <Select value={metodo} onValueChange={(v) => setMetodo(v as Metodo)}>
                <SelectTrigger className="w-24 font-mono" aria-label="Método">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="GET">GET</SelectItem>
                  <SelectItem value="POST">POST</SelectItem>
                </SelectContent>
              </Select>
              <Input
                aria-label="URL"
                value={url}
                onChange={(e) => setUrl(e.target.value)}
                placeholder="https://viacep.com.br/ws/{cep}/json/"
                className="font-mono"
              />
            </div>
            <p className="text-xs text-muted-foreground">
              Marque com chaves o que muda a cada chamada, como {'{cep}'}. Cada marcação vira um parâmetro.
            </p>
          </Passo>

          <Passo n={2} titulo="Parâmetros">
            {parametros.length === 0 ? (
              <p className="text-sm text-muted-foreground">Nenhum parâmetro. Coloque um {'{nome}'} na URL para criar.</p>
            ) : (
              <div className="space-y-3">
                {parametros.map((p) => (
                  <div key={p.nome} className="space-y-3 rounded-lg border bg-muted/30 p-3">
                    <div className="flex flex-wrap items-center justify-between gap-2">
                      <span className="font-mono text-sm">{p.nome}</span>
                      <div className="flex items-center gap-2">
                        <Label htmlFor={`obrig-${p.nome}`} className="text-xs font-normal text-muted-foreground">
                          Obrigatório
                        </Label>
                        <Switch
                          id={`obrig-${p.nome}`}
                          checked={p.obrigatorio}
                          onCheckedChange={(v) => detalhe(p.nome, { obrigatorio: v })}
                        />
                      </div>
                    </div>
                    <div className="grid gap-3 md:grid-cols-[2fr_1fr_1fr]">
                      <div className="space-y-1.5">
                        <Label htmlFor={`desc-${p.nome}`} className="text-xs">
                          Descrição
                        </Label>
                        <Input
                          id={`desc-${p.nome}`}
                          value={p.descricao}
                          onChange={(e) => detalhe(p.nome, { descricao: e.target.value })}
                          placeholder="Ex.: CEP com 8 dígitos, só números"
                        />
                      </div>
                      <div className="space-y-1.5">
                        <Label htmlFor={`tipo-${p.nome}`} className="text-xs">
                          Tipo
                        </Label>
                        <Select value={p.tipo} onValueChange={(v) => detalhe(p.nome, { tipo: v as TipoParametro })}>
                          <SelectTrigger id={`tipo-${p.nome}`} className="w-full">
                            <SelectValue />
                          </SelectTrigger>
                          <SelectContent>
                            {TIPOS.map((t) => (
                              <SelectItem key={t.valor} value={t.valor}>
                                {t.rotulo}
                              </SelectItem>
                            ))}
                          </SelectContent>
                        </Select>
                      </div>
                      <div className="space-y-1.5">
                        <Label htmlFor={`ex-${p.nome}`} className="text-xs">
                          Valor de exemplo
                        </Label>
                        <Input
                          id={`ex-${p.nome}`}
                          value={p.exemplo}
                          onChange={(e) => detalhe(p.nome, { exemplo: e.target.value })}
                          className="font-mono"
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </Passo>

          <Passo n={3} titulo="Autenticação">
            <Select value={auth.tipo} onValueChange={(v) => setAuth({ tipo: v as Auth['tipo'] })}>
              <SelectTrigger className="w-56" aria-label="Autenticação">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value="nenhuma">Nenhuma</SelectItem>
                <SelectItem value="header">Chave no header</SelectItem>
                <SelectItem value="bearer">Token Bearer</SelectItem>
              </SelectContent>
            </Select>
            {auth.tipo === 'header' && (
              <div className="grid gap-3 md:grid-cols-[1fr_2fr]">
                <div className="space-y-1.5">
                  <Label htmlFor="auth-nome" className="text-xs">
                    Nome do header
                  </Label>
                  <Input
                    id="auth-nome"
                    value={auth.nome ?? ''}
                    onChange={(e) => setAuth({ ...auth, nome: e.target.value })}
                    placeholder="X-API-Key"
                    className="font-mono"
                  />
                </div>
                <div className="space-y-1.5">
                  <Label htmlFor="auth-valor" className="text-xs">
                    Valor
                  </Label>
                  <Input
                    id="auth-valor"
                    type="password"
                    autoComplete="off"
                    value={auth.valor ?? ''}
                    onChange={(e) => setAuth({ ...auth, valor: e.target.value })}
                  />
                </div>
              </div>
            )}
            {auth.tipo === 'bearer' && (
              <div className="space-y-1.5">
                <Label htmlFor="auth-token" className="text-xs">
                  Token
                </Label>
                <Input
                  id="auth-token"
                  type="password"
                  autoComplete="off"
                  value={auth.token ?? ''}
                  onChange={(e) => setAuth({ ...auth, token: e.target.value })}
                />
              </div>
            )}
            {auth.tipo !== 'nenhuma' && (
              <p className="text-xs text-muted-foreground">Guardado cifrado. Nunca volta para a tela.</p>
            )}
          </Passo>

          <Passo n={4} titulo="Nome e descrição">
            <div className="space-y-1.5">
              <Label htmlFor="api-nome" className="text-xs">
                Nome
              </Label>
              <Input
                id="api-nome"
                value={nomeFinal}
                onChange={(e) => setNome(e.target.value.toLowerCase())}
                maxLength={LIMITE_NOME}
                placeholder="buscar_cep"
                className="font-mono"
              />
              <p className="text-xs text-muted-foreground">
                {nome === null && nomeFinal ? 'Sugerido a partir da URL. ' : ''}Letras minúsculas, números e _.
              </p>
            </div>
            <div className="space-y-1.5">
              <div className="flex items-baseline justify-between">
                <Label htmlFor="api-desc" className="text-xs">
                  Descrição
                </Label>
                <span className="text-xs text-muted-foreground tabular-nums">
                  {descricao.length}/{LIMITE_DESCRICAO}
                </span>
              </div>
              <Textarea
                id="api-desc"
                value={descricao}
                onChange={(e) => setDescricao(e.target.value)}
                maxLength={LIMITE_DESCRICAO}
                rows={2}
                placeholder="Ex.: Busca o endereço de um CEP brasileiro"
              />
              <p className="text-xs text-muted-foreground">O assistente lê este texto para decidir quando usar a tool.</p>
            </div>
          </Passo>

          {post && (
            <Passo n={5} titulo="Corpo JSON">
              <Textarea
                aria-label="Corpo JSON"
                value={corpoTexto}
                onChange={(e) => setCorpoTexto(e.target.value)}
                rows={6}
                placeholder={'{\n  "cep": "{cep}"\n}'}
                className="font-mono text-xs"
                aria-invalid={!!corpo.erro}
              />
              <p className={corpo.erro ? 'text-xs text-destructive' : 'text-xs text-muted-foreground'}>
                {corpo.erro
                  ? `JSON inválido: ${corpo.erro}`
                  : corpoTexto.trim()
                    ? 'JSON válido. "{param}" sozinho vira o valor com o tipo do parâmetro.'
                    : 'Opcional. Use "{param}" para colocar um parâmetro no corpo.'}
              </p>
            </Passo>
          )}

          {erroTeste?.chave === chave ? (
            <ErroTeste msg={erroTeste.msg} />
          ) : (
            teste && <ResultadoTeste r={teste.r} velho={teste.chave !== chave} />
          )}
        </CardContent>
        <CardFooter className="flex-col items-stretch gap-3 border-t">
          {erroSalvar && (
            <p role="alert" className="flex items-start gap-2 text-sm text-destructive">
              <AlertCircleIcon className="mt-0.5 size-4 shrink-0" /> <span className="break-words">{erroSalvar}</span>
            </p>
          )}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-muted-foreground">
              {pendencias.length
                ? `Falta ${pendencias[0]}.`
                : ok
                  ? 'Teste passou. Pode salvar.'
                  : 'Teste com os valores de exemplo para liberar o Salvar.'}
            </p>
            <div className="flex w-full gap-2 md:w-auto">
              <Button
                variant="outline"
                className="flex-1 md:flex-none"
                disabled={testando || pendencias.length > 0}
                onClick={() => void testar()}
              >
                {testando ? <Spinner /> : <FlaskConicalIcon />} Testar
              </Button>
              <Button className="flex-1 md:flex-none" disabled={!ok || salvando} onClick={() => void salvar()}>
                {salvando ? <Spinner /> : <SaveIcon />} Salvar
              </Button>
            </div>
          </div>
        </CardFooter>
      </Card>
    </section>
  )
}

function formatado(texto: string): { codigo: string; json: boolean } {
  try {
    return { codigo: JSON.stringify(JSON.parse(texto), null, 2), json: true }
  } catch {
    return { codigo: texto, json: false }
  }
}

function ErroTeste({ msg }: { msg: string }) {
  return (
    <div role="alert" className="flex items-start gap-2 rounded-lg border border-destructive/40 bg-destructive/10 p-3 text-sm">
      <XCircleIcon className="mt-0.5 size-4 shrink-0 text-destructive" />
      <span className="break-words">{msg}</span>
    </div>
  )
}

function ResultadoTeste({ r, velho }: { r: Teste; velho: boolean }) {
  const ok = r.status >= 200 && r.status < 300
  const { codigo, json } = formatado(r.corpo_cortado)
  return (
    <div className={velho ? 'space-y-2 opacity-60' : 'space-y-2'}>
      <div className="flex flex-wrap items-center gap-2 text-sm">
        {ok ? (
          <CheckCircle2Icon className="size-4 text-emerald-500" />
        ) : (
          <XCircleIcon className="size-4 text-destructive" />
        )}
        <span className="font-medium">{ok ? 'A API respondeu' : 'A API respondeu com erro'}</span>
        <Badge variant={ok ? 'secondary' : 'destructive'} className="font-mono">
          {r.status}
        </Badge>
        <span className="text-muted-foreground tabular-nums">{r.ms} ms</span>
        {velho && <span className="text-xs text-muted-foreground">A definição mudou. Teste de novo.</span>}
      </div>
      {!ok && (
        <p className="text-sm text-muted-foreground">
          Confira a URL e o valor de exemplo. Só um teste com resposta 2xx libera o Salvar.
        </p>
      )}
      <div className="max-h-72 overflow-auto rounded-md bg-muted/50">
        {json ? (
          <CodeBlock code={codigo} language="json" />
        ) : (
          <pre className="p-4 font-mono text-xs break-all whitespace-pre-wrap">{codigo || '(resposta vazia)'}</pre>
        )}
      </div>
    </div>
  )
}

function CardApiTool({ t, onRemover }: { t: ApiTool; onRemover: (t: ApiTool) => void }) {
  const n = t.parametros.length
  return (
    <Card>
      <CardHeader>
        <CardTitle className="flex flex-wrap items-center gap-2 text-base">
          <GlobeIcon className="size-4 text-muted-foreground" /> <span className="font-mono">{t.nome}</span>
          <Badge variant="outline" className="font-mono">
            {t.metodo}
          </Badge>
          <Badge variant="secondary">
            {n} {n === 1 ? 'parâmetro' : 'parâmetros'}
          </Badge>
          {t.auth_tipo !== 'nenhuma' && (
            <Badge variant="outline" className="font-normal">
              com autenticação
            </Badge>
          )}
        </CardTitle>
        <CardDescription className="space-y-1">
          <span className="block truncate font-mono text-xs" title={t.url}>
            {host(t.url)}
          </span>
          <span className="line-clamp-2 block">{t.descricao}</span>
        </CardDescription>
      </CardHeader>
      <CardFooter className="justify-between text-xs text-muted-foreground">
        <span>Adicionada em {fmtData.format(new Date(t.created_at))}</span>
        <Button variant="outline" size="sm" onClick={() => onRemover(t)}>
          <Trash2Icon /> Remover
        </Button>
      </CardFooter>
    </Card>
  )
}
