import { useEffect, useState } from 'react'
import { CheckCircle2Icon, CornerUpLeftIcon, MailIcon, SendIcon, Trash2Icon, XCircleIcon } from 'lucide-react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Spinner } from '@/components/ui/spinner'
import { ErroApi } from '@/lib/api'
import { descartarRascunho, enviarRascunho, lerRascunho, type EstadoRascunho } from '@/lib/conectores'

// Rascunho de e-mail dentro da mensagem do assistente (ADR 0013). Só o clique em Enviar manda o e-mail.

export type SaidaRascunho = {
  draft_id: string
  estado: EstadoRascunho
  para: string
  assunto: string
  corpo: string
  thread_id: string | null
}

export const ehRascunho = (x: unknown): x is SaidaRascunho =>
  typeof x === 'object' && x !== null && typeof (x as SaidaRascunho).draft_id === 'string'

const ROTULO: Record<EstadoRascunho, string> = { pendente: 'Aguardando você', enviado: 'Enviado', descartado: 'Descartado' }

export function RascunhoEmail({ saida }: { saida: SaidaRascunho }) {
  // A parte gravada na Mensagem fica em "pendente". O estado real vem do servidor.
  const [estado, setEstado] = useState<EstadoRascunho>(saida.estado)
  const [dono, setDono] = useState(true)
  const [acao, setAcao] = useState<'enviar' | 'descartar' | null>(null)
  const [erro, setErro] = useState<string | null>(null)

  useEffect(() => {
    let vivo = true
    lerRascunho(saida.draft_id)
      .then((r) => vivo && setEstado(r.estado))
      .catch(() => vivo && setDono(false))
    return () => {
      vivo = false
    }
  }, [saida.draft_id])

  async function decidir(qual: 'enviar' | 'descartar') {
    setAcao(qual)
    setErro(null)
    try {
      const r = await (qual === 'enviar' ? enviarRascunho : descartarRascunho)(saida.draft_id)
      setEstado(r.estado)
    } catch (e) {
      const detalhe = e instanceof ErroApi && typeof e.detail === 'string' ? e.detail : null
      setErro(detalhe ?? 'Não foi possível concluir. Tente de novo.')
      // 409: outro clique já decidiu. Relê para mostrar o estado certo.
      if (e instanceof ErroApi && e.status === 409) void lerRascunho(saida.draft_id).then((r) => setEstado(r.estado))
    } finally {
      setAcao(null)
    }
  }

  const pendente = estado === 'pendente'
  return (
    <Card className="gap-3 py-4" aria-label="Rascunho de e-mail">
      <CardHeader className="px-4">
        <CardTitle className="flex items-center gap-2 text-sm font-medium">
          <MailIcon className="size-4 text-muted-foreground" />
          Rascunho de e-mail
          <Badge variant={pendente ? 'outline' : 'secondary'} className="ml-auto font-normal">
            {estado === 'enviado' && <CheckCircle2Icon className="text-emerald-500" />}
            {estado === 'descartado' && <XCircleIcon />}
            {ROTULO[estado]}
          </Badge>
        </CardTitle>
      </CardHeader>
      <CardContent className="space-y-3 px-4 text-sm">
        <dl className="grid grid-cols-[auto_1fr] gap-x-3 gap-y-1">
          <dt className="text-muted-foreground">Para</dt>
          <dd className="min-w-0 break-words">{saida.para}</dd>
          <dt className="text-muted-foreground">Assunto</dt>
          <dd className="min-w-0 break-words">{saida.assunto}</dd>
        </dl>
        {saida.thread_id && (
          <p className="flex items-center gap-1.5 text-xs text-muted-foreground">
            <CornerUpLeftIcon className="size-3.5" /> Resposta na mesma conversa do Gmail
          </p>
        )}
        <div className="rounded-md border bg-muted/40 p-3 whitespace-pre-wrap">{saida.corpo}</div>
        {erro && (
          <p className="text-sm text-destructive" role="alert">
            {erro}
          </p>
        )}
      </CardContent>
      {pendente && dono && (
        <CardFooter className="justify-end gap-2 px-4">
          <Button variant="outline" size="sm" disabled={acao !== null} onClick={() => void decidir('descartar')}>
            {acao === 'descartar' ? <Spinner /> : <Trash2Icon />} Descartar
          </Button>
          <Button size="sm" disabled={acao !== null} onClick={() => void decidir('enviar')}>
            {acao === 'enviar' ? <Spinner /> : <SendIcon />} Enviar
          </Button>
        </CardFooter>
      )}
    </Card>
  )
}
