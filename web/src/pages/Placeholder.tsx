/** Tela placeholder até o ticket da funcionalidade. */
export function Placeholder({ titulo }: { titulo: string }) {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-semibold">{titulo}</h1>
      <p className="mt-2 text-muted-foreground">Em construção.</p>
    </div>
  )
}
