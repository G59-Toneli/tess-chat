import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router'
import { CopyIcon, ExternalLinkIcon, Link2OffIcon } from 'lucide-react'
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
import { Button } from '@/components/ui/button'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { cn } from '@/lib/utils'
import { copiar, listarShares, revogarShare, urlAbsoluta, type Share } from '@/lib/shares'

const fmtData = new Intl.DateTimeFormat('pt-BR', { dateStyle: 'short', timeStyle: 'short' })

/** Meus links (/compartilhados): abrir, copiar, revogar. */
export function Compartilhados() {
  const [shares, setShares] = useState<Share[] | null>(null)
  const [erro, setErro] = useState(false)
  const [revogando, setRevogando] = useState<Share | null>(null)

  const carregar = useCallback(async () => {
    setErro(false)
    setShares(null)
    try {
      setShares(await listarShares())
    } catch {
      setErro(true)
    }
  }, [])

  useEffect(() => void carregar(), [carregar])

  async function copiarLink(s: Share) {
    if (await copiar(urlAbsoluta(s))) toast.success('Link copiado.')
    else toast.error('Não foi possível copiar o link.')
  }

  async function revogar() {
    if (!revogando) return
    try {
      await revogarShare(revogando.id)
      setShares((l) => l?.filter((s) => s.id !== revogando.id) ?? null)
      toast.success('Link revogado. Quem abrir verá “link indisponível”.')
    } catch {
      toast.error('Não foi possível revogar o link.')
    }
    setRevogando(null)
  }

  return (
    <div className="mx-auto max-w-4xl p-4 md:p-8">
      <h1 className="text-2xl font-semibold">Compartilhados</h1>
      <p className="mt-1 mb-6 text-sm text-muted-foreground">
        Links públicos das suas conversas. Cada link mostra a conversa até o momento em que foi criado.
      </p>
      {erro ? (
        <EstadoErro mensagem="Não foi possível carregar os links." onTentarDeNovo={carregar} />
      ) : shares === null ? (
        <EstadoCarregando />
      ) : shares.length === 0 ? (
        <EstadoVazio
          titulo="Nenhum link ainda"
          descricao="Abra o menu de uma conversa na barra lateral e clique em Compartilhar."
          acao={
            <Button variant="outline" asChild>
              <Link to="/">Ir para as conversas</Link>
            </Button>
          }
        />
      ) : (
        <ul className="divide-y rounded-lg border">
          {shares.map((s) => (
            <li key={s.id} className="flex items-center gap-4 px-4 py-3">
              <div className="min-w-0 flex-1">
                <Link to={`/c/${s.conversation_id}`} className="block truncate font-medium hover:underline">
                  {s.title}
                </Link>
                <p className="truncate text-xs text-muted-foreground">
                  Criado em {fmtData.format(new Date(s.created_at))} · {urlAbsoluta(s)}
                </p>
              </div>
              <div className="flex shrink-0 gap-1">
                <Acao rotulo="Abrir link" onClick={() => window.open(s.url, '_blank', 'noopener')}>
                  <ExternalLinkIcon />
                </Acao>
                <Acao rotulo="Copiar link" onClick={() => copiarLink(s)}>
                  <CopyIcon />
                </Acao>
                <Acao rotulo="Revogar link" onClick={() => setRevogando(s)} destrutivo>
                  <Link2OffIcon />
                </Acao>
              </div>
            </li>
          ))}
        </ul>
      )}
      <AlertDialog open={revogando !== null} onOpenChange={(aberto) => !aberto && setRevogando(null)}>
        <AlertDialogContent>
          <AlertDialogHeader>
            <AlertDialogTitle>Revogar link?</AlertDialogTitle>
            <AlertDialogDescription>
              O link de “{revogando?.title}” para de funcionar para todo mundo. A conversa continua com você.
            </AlertDialogDescription>
          </AlertDialogHeader>
          <AlertDialogFooter>
            <AlertDialogCancel>Cancelar</AlertDialogCancel>
            <AlertDialogAction variant="destructive" onClick={revogar}>
              Revogar
            </AlertDialogAction>
          </AlertDialogFooter>
        </AlertDialogContent>
      </AlertDialog>
    </div>
  )
}

function Acao({
  rotulo,
  onClick,
  destrutivo,
  children,
}: {
  rotulo: string
  onClick: () => void
  destrutivo?: boolean
  children: React.ReactNode
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="ghost"
          size="icon-sm"
          aria-label={rotulo}
          onClick={onClick}
          className={cn('size-10 md:size-8', destrutivo && 'text-destructive hover:text-destructive')}
        >
          {children}
        </Button>
      </TooltipTrigger>
      <TooltipContent>{rotulo}</TooltipContent>
    </Tooltip>
  )
}
