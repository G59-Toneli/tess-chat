import type { ReactNode } from 'react'
import { AlertCircleIcon, InboxIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Empty, EmptyContent, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { Skeleton } from '@/components/ui/skeleton'
import { Spinner } from '@/components/ui/spinner'

// Estados de tela reutilizáveis (docs/UI-GUIA.md): vazio, carregando, erro.

export function EstadoVazio({ titulo, descricao, acao }: { titulo: string; descricao: string; acao?: ReactNode }) {
  return (
    <Empty>
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <InboxIcon />
        </EmptyMedia>
        <EmptyTitle>{titulo}</EmptyTitle>
        <EmptyDescription>{descricao}</EmptyDescription>
      </EmptyHeader>
      {acao && <EmptyContent>{acao}</EmptyContent>}
    </Empty>
  )
}

export function EstadoCarregando() {
  return (
    <div className="flex flex-col gap-3" role="status" aria-label="Carregando">
      <div className="flex items-center gap-2 text-sm text-muted-foreground">
        <Spinner /> Carregando...
      </div>
      <Skeleton className="h-8 w-1/2" />
      <Skeleton className="h-4 w-full" />
      <Skeleton className="h-4 w-5/6" />
    </div>
  )
}

export function EstadoErro({ mensagem, onTentarDeNovo }: { mensagem: string; onTentarDeNovo: () => void }) {
  return (
    <Empty>
      <EmptyHeader>
        <EmptyMedia variant="icon">
          <AlertCircleIcon className="text-destructive" />
        </EmptyMedia>
        <EmptyTitle>Algo deu errado</EmptyTitle>
        <EmptyDescription>{mensagem}</EmptyDescription>
      </EmptyHeader>
      <EmptyContent>
        <Button variant="outline" onClick={onTentarDeNovo}>
          Tentar de novo
        </Button>
      </EmptyContent>
    </Empty>
  )
}
