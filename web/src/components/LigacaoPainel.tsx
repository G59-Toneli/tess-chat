// Painel da Ligação estilo Discord, no topo da Conversa (ticket 78). Montar liga; desmontar encerra.
import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import {
  AlertCircleIcon,
  MicIcon,
  MicOffIcon,
  MonitorOffIcon,
  MonitorUpIcon,
  PhoneIcon,
  PhoneOffIcon,
  WalletIcon,
} from 'lucide-react'
import { IconeApp } from '@/components/Logo'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Spinner } from '@/components/ui/spinner'
import { Tooltip, TooltipContent, TooltipTrigger } from '@/components/ui/tooltip'
import { iniciais } from '@/lib/datas'
import { useLigacao, type EstadoLigacao, type Fala, type Ligacao } from '@/lib/ligacao/useLigacao'
import { cn } from '@/lib/utils'

export function BotaoLigacao({ onClick, disabled }: { onClick: () => void; disabled?: boolean }) {
  return (
    <Button variant="ghost" className="h-10 gap-2 px-3 md:h-8" onClick={onClick} disabled={disabled} aria-label="Iniciar ligação">
      <PhoneIcon /> <span className="hidden sm:inline">Ligar</span>
    </Button>
  )
}

/** "Tentar de novo" remonta o painel: ticket e WebSocket novos. */
/** `onAtiva`: true enquanto a Ligação conecta ou está no ar; false no erro e no fim. */
export function LigacaoPainel(props: {
  conversaId: string
  email?: string
  onFechar: () => void
  onAtiva: (ativa: boolean) => void
}) {
  const [tentativa, setTentativa] = useState(0)
  return <Painel key={tentativa} {...props} onTentarDeNovo={() => setTentativa((t) => t + 1)} />
}

const ROTULO: Record<EstadoLigacao, string> = {
  conectando: 'Conectando…',
  em_ligacao: 'Em ligação',
  encerrando: 'Encerrando…',
  encerrada: 'Ligação encerrada',
  erro: 'Ligação não conectou',
}

function Painel({
  conversaId,
  email,
  onFechar,
  onAtiva,
  onTentarDeNovo,
}: {
  conversaId: string
  email?: string
  onFechar: () => void
  onAtiva: (ativa: boolean) => void
  onTentarDeNovo: () => void
}) {
  const l = useLigacao(conversaId)
  const fim = l.estado === 'erro' || l.estado === 'encerrada'

  useEffect(() => onAtiva(!fim), [fim, onAtiva])

  // Quem desligou foi o usuário: o painel fecha sozinho quando o servidor confirma.
  useEffect(() => {
    if (l.estado === 'encerrada' && l.desligouAqui) onFechar()
  }, [l.estado, l.desligouAqui, onFechar])

  return (
    <section
      aria-label="Ligação"
      data-estado={l.estado}
      data-fila={l.fila}
      className="mt-3 shrink-0 space-y-3 rounded-xl border bg-card p-3 shadow-sm md:p-4"
    >
      <div className="flex items-center gap-2">
        <IndicadorEstado estado={l.estado} />
        <span className="text-sm font-medium">{ROTULO[l.estado]}</span>
        {l.inicio !== null && !fim && <Contador inicio={l.inicio} limiteS={l.limiteS} />}
      </div>

      {fim ? (
        <Aviso ligacao={l} onFechar={onFechar} onTentarDeNovo={onTentarDeNovo} />
      ) : (
        <>
          <div className={cn('grid grid-cols-2 gap-2 md:gap-3', l.tela && 'md:grid-cols-3')}>
            <Participante
              nome="Você"
              avatar={
                <Avatar className="size-12">
                  <AvatarFallback>{email ? iniciais(email) : 'EU'}</AvatarFallback>
                </Avatar>
              }
              mudo={l.mudo}
            />
            <Participante nome="Assistente" avatar={<IconeApp className="size-12 rounded-full" />} falando={l.fila > 0} pensando={l.pensando && l.fila === 0} />
            {l.tela && <PreviaTela stream={l.tela} />}
          </div>
          <Transcricao falas={l.falas} />
          {l.aviso && l.estado === 'em_ligacao' && (
            <p role="status" className="text-sm text-destructive">
              {l.aviso}
            </p>
          )}
          <Controles ligacao={l} onCancelar={onFechar} />
        </>
      )}
    </section>
  )
}

function IndicadorEstado({ estado }: { estado: EstadoLigacao }) {
  if (estado === 'conectando' || estado === 'encerrando') return <Spinner className="size-4 text-muted-foreground" />
  if (estado === 'erro') return <AlertCircleIcon className="size-4 text-destructive" />
  return (
    <span className={cn('size-2.5 rounded-full', estado === 'em_ligacao' ? 'animate-pulse bg-emerald-500' : 'bg-muted-foreground')} />
  )
}

const mmss = (s: number) => `${String(Math.floor(s / 60)).padStart(2, '0')}:${String(Math.floor(s % 60)).padStart(2, '0')}`

function Contador({ inicio, limiteS }: { inicio: number; limiteS: number }) {
  const [agora, setAgora] = useState(() => Date.now())
  useEffect(() => {
    const t = setInterval(() => setAgora(Date.now()), 1000)
    return () => clearInterval(t)
  }, [])
  const passou = Math.min(limiteS, Math.max(0, (agora - inicio) / 1000))
  // Último minuto em destaque: a Ligação cai no limite.
  const fim = limiteS - passou <= 60
  return (
    <span
      className={cn('ml-auto font-mono text-sm tabular-nums', fim ? 'text-destructive' : 'text-muted-foreground')}
      aria-label={`Tempo de ligação ${mmss(passou)} de ${mmss(limiteS)}`}
    >
      {mmss(passou)} / {mmss(limiteS)}
    </span>
  )
}

function Participante({
  nome,
  avatar,
  falando,
  pensando,
  mudo,
}: {
  nome: string
  avatar: React.ReactNode
  falando?: boolean
  pensando?: boolean
  mudo?: boolean
}) {
  return (
    <div
      data-falando={falando || undefined}
      data-pensando={pensando || undefined}
      className="flex h-24 flex-col items-center justify-center gap-1.5 rounded-lg bg-muted/60 md:h-28"
    >
      <span
        className={cn(
          'rounded-full ring-2 ring-offset-2 ring-offset-muted transition-shadow',
          falando ? 'ring-emerald-500' : 'ring-transparent',
        )}
      >
        {avatar}
      </span>
      <span className="flex items-center gap-1 text-xs text-muted-foreground">
        {nome}
        {mudo && <MicOffIcon className="size-3 text-destructive" aria-label="microfone mudo" />}
        {falando && <span className="sr-only">falando</span>}
        {pensando && (
          <span className="flex items-center gap-1">
            <Spinner className="size-3" /> pensando…
          </span>
        )}
      </span>
    </div>
  )
}

function PreviaTela({ stream }: { stream: MediaStream }) {
  const ref = useRef<HTMLVideoElement>(null)
  useEffect(() => {
    if (ref.current) ref.current.srcObject = stream
  }, [stream])
  return (
    <div className="relative col-span-2 h-24 overflow-hidden rounded-lg bg-muted/60 md:col-span-1 md:h-28">
      <video ref={ref} autoPlay muted playsInline className="size-full object-contain" aria-label="Prévia da tela compartilhada" />
      <span className="absolute bottom-1 left-1 rounded bg-background/80 px-1.5 py-0.5 text-[11px] text-muted-foreground">
        Sua tela
      </span>
    </div>
  )
}

function Transcricao({ falas }: { falas: Fala[] }) {
  const ref = useRef<HTMLDivElement>(null)
  useEffect(() => {
    ref.current?.scrollTo({ top: ref.current.scrollHeight })
  }, [falas])
  return (
    <div
      ref={ref}
      aria-live="polite"
      aria-label="Transcrição"
      className="max-h-24 space-y-1 overflow-y-auto rounded-lg border bg-background/50 px-3 py-2 text-sm md:max-h-36"
    >
      {falas.length === 0 ? (
        <p className="text-muted-foreground">A transcrição aparece aqui quando alguém falar.</p>
      ) : (
        falas.map((f) => (
          <p key={f.id} className={cn('wrap-anywhere', !f.final && 'text-muted-foreground')}>
            <span className="mr-1.5 font-medium text-foreground">{f.origem === 'usuario' ? 'Você' : 'Assistente'}</span>
            {f.texto.trim()}
          </p>
        ))
      )}
    </div>
  )
}

function BotaoControle({
  rotulo,
  onClick,
  disabled,
  className,
  children,
}: {
  rotulo: string
  onClick: () => void
  disabled?: boolean
  className?: string
  children: React.ReactNode
}) {
  return (
    <Tooltip>
      <TooltipTrigger asChild>
        <Button
          variant="secondary"
          className={cn('size-10 rounded-full', className)}
          onClick={onClick}
          disabled={disabled}
          aria-label={rotulo}
        >
          {children}
        </Button>
      </TooltipTrigger>
      <TooltipContent>{rotulo}</TooltipContent>
    </Tooltip>
  )
}

function Controles({ ligacao: l, onCancelar }: { ligacao: Ligacao; onCancelar: () => void }) {
  const ativa = l.estado === 'em_ligacao'
  return (
    <div className="flex items-center justify-center gap-3">
      <BotaoControle
        rotulo={l.mudo ? 'Ativar microfone' : 'Mutar microfone'}
        onClick={l.alternarMudo}
        disabled={!ativa}
        className={cn(l.mudo && 'bg-destructive/20 text-destructive hover:bg-destructive/30')}
      >
        {l.mudo ? <MicOffIcon /> : <MicIcon />}
      </BotaoControle>
      {l.telaSuportada && (
        <BotaoControle
          rotulo={l.tela ? 'Parar de compartilhar' : 'Compartilhar tela'}
          onClick={() => void l.alternarTela()}
          disabled={!ativa}
          className={cn(l.tela && 'bg-primary text-primary-foreground hover:bg-primary/80')}
        >
          {l.tela ? <MonitorOffIcon /> : <MonitorUpIcon />}
        </BotaoControle>
      )}
      <BotaoControle
        rotulo="Desligar"
        // Antes do `pronto` não há Ligação no servidor: fechar o painel já solta microfone e conexão.
        onClick={l.estado === 'conectando' ? onCancelar : l.desligar}
        disabled={l.estado === 'encerrando'}
        className="w-14 bg-destructive text-white hover:bg-destructive/85"
      >
        <PhoneOffIcon />
      </BotaoControle>
    </div>
  )
}

function Aviso({ ligacao: l, onFechar, onTentarDeNovo }: { ligacao: Ligacao; onFechar: () => void; onTentarDeNovo: () => void }) {
  const erro = l.estado === 'erro'
  return (
    <div
      role={erro ? 'alert' : 'status'}
      className={cn('flex flex-col gap-3 rounded-lg border p-3 sm:flex-row sm:items-center', erro ? 'border-destructive/40 bg-destructive/10' : 'bg-muted/40')}
    >
      <div className="flex flex-1 items-start gap-2">
        {l.cap ? (
          <WalletIcon className="mt-0.5 size-4 shrink-0 text-destructive" />
        ) : (
          erro && <AlertCircleIcon className="mt-0.5 size-4 shrink-0 text-destructive" />
        )}
        <p className="text-sm">{l.aviso}</p>
      </div>
      <div className="flex flex-wrap gap-2">
        {l.cap && (
          <Button asChild size="sm" className="max-md:h-10">
            <Link to="/creditos">Ver créditos</Link>
          </Button>
        )}
        {erro && !l.cap && (
          <Button size="sm" className="max-md:h-10" onClick={onTentarDeNovo}>
            Tentar de novo
          </Button>
        )}
        <Button size="sm" variant="outline" className="max-md:h-10" onClick={onFechar}>
          Fechar
        </Button>
      </div>
    </div>
  )
}
