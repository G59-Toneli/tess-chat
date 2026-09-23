import { FoldVerticalIcon } from 'lucide-react'

/** Mostra a Mensagem e, se o Resumo cobre até ela, o marcador logo depois. */
export function MarcadorCompactacao({ aqui, children }: { aqui: boolean; children: React.ReactNode }) {
  return (
    <>
      {children}
      {aqui && (
        <div role="separator" className="flex items-center gap-3 text-xs text-muted-foreground">
          <span className="h-px flex-1 bg-border" />
          <FoldVerticalIcon className="size-3.5" />
          Histórico compactado aqui
          <span className="h-px flex-1 bg-border" />
        </div>
      )}
    </>
  )
}
