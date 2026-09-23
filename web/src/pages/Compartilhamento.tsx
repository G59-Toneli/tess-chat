import { Link, useParams } from 'react-router'

/** Compartilhamento público somente-leitura. Placeholder. */
export function Compartilhamento() {
  const { shareId } = useParams()
  return (
    <div className="mx-auto max-w-3xl p-8">
      <h1 className="text-2xl font-semibold">Conversa compartilhada</h1>
      <p className="mt-2 text-muted-foreground">Link {shareId}. Somente leitura. Em construção.</p>
      <Link to="/login" className="mt-4 inline-block underline">
        Entrar
      </Link>
    </div>
  )
}
