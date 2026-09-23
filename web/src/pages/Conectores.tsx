import { useCallback, useEffect, useState } from 'react'
import { useSearchParams } from 'react-router'
import { CheckCircle2Icon, CircleOffIcon, HardDriveIcon, Link2OffIcon, MailIcon, PlugIcon, RefreshCwIcon, SendIcon, TriangleAlertIcon } from 'lucide-react'
import { toast } from 'sonner'
import { EstadoCarregando, EstadoErro } from '@/components/estados'
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
import { Spinner } from '@/components/ui/spinner'
import {
  listarConectores,
  revogarGoogle,
  rotuloEscopo,
  semEnvio,
  textoErroOAuth,
  urlDoGoogle,
  type Conector,
} from '@/lib/conectores'

const fmtData = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' })
const ESCOPOS_PADRAO = ['Gmail (leitura)', 'Drive (leitura)', 'Gmail (envio com confirmação)']

/** /conectores: conectar, reconectar e revogar o Google (Gmail e Drive; envio só com clique). */
export function Conectores() {
  const [google, setGoogle] = useState<Conector | null>(null)
  const [erro, setErro] = useState(false)
  const [indo, setIndo] = useState(false)
  const [revogando, setRevogando] = useState(false)
  const [params, setParams] = useSearchParams()

  const carregar = useCallback(async () => {
    setErro(false)
    setGoogle(null)
    try {
      const lista = await listarConectores()
      setGoogle(lista.find((c) => c.provedor === 'google') ?? null)
    } catch {
      setErro(true)
    }
  }, [])

  useEffect(() => void carregar(), [carregar])

  // Volta do Google: avisa e limpa a query.
  useEffect(() => {
    const codigo = params.get('erro')
    if (params.get('sem_gmail')) toast.warning('Google conectado, mas esta conta não tem Gmail. Só o Drive funciona.', { id: 'oauth' })
    else if (params.get('conectado')) toast.success('Google conectado. Gmail e Drive já estão nas suas conversas.', { id: 'oauth' })
    else if (codigo) toast.error(textoErroOAuth(codigo), { id: 'oauth' })
    else return
    setParams({}, { replace: true })
  }, [params, setParams])

  async function conectar() {
    setIndo(true)
    try {
      window.location.assign((await urlDoGoogle()).url)
    } catch {
      toast.error('Não foi possível iniciar a conexão com o Google. Tente de novo.')
      setIndo(false)
    }
  }

  async function revogar() {
    try {
      await revogarGoogle()
      toast.success('Google desconectado.')
      void carregar()
    } catch {
      toast.error('Não foi possível desconectar. Tente de novo.')
    }
  }

  const escopos = google?.conectado ? google.escopos.map(rotuloEscopo) : ESCOPOS_PADRAO
  const tokenValido = google?.expira_em && new Date(google.expira_em) > new Date()

  return (
    <div className="mx-auto h-full max-w-3xl space-y-6 overflow-y-auto px-4 py-8">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">Conectores</h1>
        <p className="text-sm text-muted-foreground">
          Um conector dá ao assistente acesso a uma conta sua. As tools dele só aparecem nas conversas depois de
          conectar.
        </p>
      </div>
      {erro ? (
        <EstadoErro mensagem="Não foi possível carregar os conectores." onTentarDeNovo={carregar} />
      ) : !google ? (
        <EstadoCarregando />
      ) : (
        <Card>
          <CardHeader>
            <CardTitle className="flex items-center gap-2 text-base">
              Google
              {google.conectado ? (
                <Badge variant="secondary">
                  <CheckCircle2Icon className="text-emerald-500" /> Conectado
                </Badge>
              ) : (
                <Badge variant="outline" className="text-muted-foreground">
                  <CircleOffIcon /> Desconectado
                </Badge>
              )}
            </CardTitle>
            <CardDescription>
              Buscar e ler e-mails do Gmail e arquivos do Drive. O assistente pode preparar respostas, mas um e-mail só
              sai quando você clica em Enviar no rascunho. Nada é apagado nem alterado.
            </CardDescription>
          </CardHeader>
          <CardContent className="space-y-4 text-sm">
            <div className="flex flex-wrap gap-2">
              {escopos.map((e) => (
                <Badge key={e} variant="outline" className="font-normal">
                  {e.includes('envio') ? <SendIcon /> : e.startsWith('Gmail') ? <MailIcon /> : <HardDriveIcon />} {e}
                </Badge>
              ))}
            </div>
            {google.conectado && !google.gmail_disponivel && (
              <div
                className="flex items-start gap-3 rounded-md border border-amber-500/40 bg-amber-500/10 p-3"
                role="alert"
              >
                <TriangleAlertIcon className="mt-0.5 size-4 shrink-0 text-amber-500" />
                <div className="flex-1 space-y-1">
                  <p className="font-medium">Esta conta não tem Gmail</p>
                  <p className="text-muted-foreground">
                    Esta conta Google não tem caixa Gmail (é uma conta criada com um e-mail de outro provedor). Buscar,
                    ler e enviar e-mails não vão funcionar. Conecte uma conta @gmail.com ou Workspace com Gmail ativo. O
                    Drive continua funcionando.
                  </p>
                </div>
              </div>
            )}
            {semEnvio(google) && google.gmail_disponivel && (
              <div className="flex items-start gap-3 rounded-md border bg-muted/40 p-3" role="status">
                <SendIcon className="mt-0.5 size-4 shrink-0 text-muted-foreground" />
                <div className="flex-1 space-y-1">
                  <p className="font-medium">Reconecte para enviar e-mails</p>
                  <p className="text-muted-foreground">
                    Esta conexão é anterior ao envio. Reconecte e aceite a permissão de envio para liberar a tool{' '}
                    <span className="font-mono">gmail_send</span>.
                  </p>
                </div>
                <Button size="sm" variant="outline" onClick={() => void conectar()} disabled={indo}>
                  {indo ? <Spinner /> : <RefreshCwIcon />} Reconectar
                </Button>
              </div>
            )}
            {google.conectado ? (
              <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-1 text-muted-foreground">
                <dt>Conta</dt>
                <dd className="min-w-0 break-words text-foreground">
                  {google.conta_email ? (
                    <>
                      Conectado como <span className="font-medium">{google.conta_email}</span>
                    </>
                  ) : (
                    <span className="text-muted-foreground">
                      {google.gmail_disponivel ? 'Reconecte para ver a conta' : 'não identificada'}
                    </span>
                  )}
                </dd>
                <dt>Conectado em</dt>
                <dd className="text-foreground">
                  {google.conectado_em ? fmtData.format(new Date(google.conectado_em)) : '—'}
                </dd>
                <dt>Token de acesso</dt>
                <dd className="text-foreground">
                  {tokenValido
                    ? `válido até ${fmtData.format(new Date(google.expira_em!))}`
                    : 'vencido, renova sozinho na próxima chamada'}
                </dd>
              </dl>
            ) : (
              <p className="text-muted-foreground">
                Tools liberadas ao conectar: <span className="font-mono">gmail_search</span>,{' '}
                <span className="font-mono">gmail_read</span>, <span className="font-mono">drive_search_read</span> e{' '}
                <span className="font-mono">gmail_send</span> (só prepara o rascunho; o e-mail sai quando você clica em
                Enviar).
              </p>
            )}
          </CardContent>
          <CardFooter className="justify-end gap-2">
            {google.conectado ? (
              <>
                <Button variant="ghost" onClick={() => void conectar()} disabled={indo}>
                  {indo ? <Spinner /> : <RefreshCwIcon />} Reconectar
                </Button>
                <Button variant="outline" onClick={() => setRevogando(true)}>
                  <Link2OffIcon /> Desconectar
                </Button>
              </>
            ) : (
              <Button onClick={() => void conectar()} disabled={indo}>
                {indo ? <Spinner /> : <PlugIcon />} Conectar Google
              </Button>
            )}
          </CardFooter>
        </Card>
      )}
      <AlertDialog open={revogando} onOpenChange={setRevogando}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Desconectar o Google?</AlertDialogTitle>
            <AlertDialogDescription>
              O acesso é revogado no Google e as tools do Gmail e do Drive somem das suas conversas. Você pode conectar
              de novo depois.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction onClick={() => void revogar()}>Desconectar</AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}
