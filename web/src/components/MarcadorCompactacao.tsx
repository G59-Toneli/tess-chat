import { useEffect, useState } from 'react'
import { FoldVerticalIcon } from 'lucide-react'
import { authHeader } from '@/lib/api'

// Corte do Resumo vigente por Conversa. Uma busca por Conversa, dividida entre as Mensagens.
const cortes = new Map<string, Promise<number | null>>()

function corteDa(conversaId: string): Promise<number | null> {
  let p = cortes.get(conversaId)
  if (!p) {
    p = fetch(`/api/chat/${conversaId}/compactacao`, { headers: authHeader() })
      .then((r) => (r.ok ? r.json() : { ate_message_id: null }))
      .then((j: { ate_message_id: number | null }) => j.ate_message_id)
      .catch(() => null)
    cortes.set(conversaId, p)
  }
  return p
}

/** Mostra a Mensagem e, se o Resumo cobre até ela, o marcador logo depois. */
export function MarcadorCompactacao({
  conversaId,
  mensagemId,
  children,
}: {
  conversaId: string
  mensagemId: string
  children: React.ReactNode
}) {
  const [corte, setCorte] = useState<number | null>(null)
  useEffect(() => {
    let vivo = true
    void corteDa(conversaId).then((c) => vivo && setCorte(c))
    return () => {
      vivo = false
    }
  }, [conversaId])

  return (
    <>
      {children}
      {corte !== null && String(corte) === mensagemId && (
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
