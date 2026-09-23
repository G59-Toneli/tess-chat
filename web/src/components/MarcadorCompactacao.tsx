import { FoldVerticalIcon } from 'lucide-react'

/** Mostra a Mensagem e, se ela é a pergunta do turno que compactou, o separador logo antes. */
export function MarcadorCompactacao({ aqui, children }: { aqui: boolean; children: React.ReactNode }) {
  return (
    <>
      {aqui && (
        <div role="separator" className="flex items-center gap-3 text-xs text-muted-foreground">
          <span className="h-px flex-1 bg-border" />
          <FoldVerticalIcon className="size-3.5" />
          Histórico anterior resumido
          <span className="h-px flex-1 bg-border" />
        </div>
      )}
      {children}
    </>
  )
}
