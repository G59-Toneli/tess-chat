import { useCallback, useEffect, useState } from 'react'
import { toast } from 'sonner'
import { CodeBlock } from '@/components/ai-elements/code-block'
import { EstadoCarregando, EstadoErro, EstadoVazio } from '@/components/estados'
import { Badge } from '@/components/ui/badge'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Collapsible, CollapsibleContent, CollapsibleTrigger } from '@/components/ui/collapsible'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { ChevronDownIcon } from 'lucide-react'
import { alternarGlobal, listarCatalogo, type ToolCatalogo } from '@/lib/tools'

/** /tools: catálogo de Tools nativas e MCP, com liga/desliga global e schema. */
export function Tools() {
  const [tools, setTools] = useState<ToolCatalogo[] | null>(null)
  const [erro, setErro] = useState(false)

  const carregar = useCallback(async () => {
    setErro(false)
    try {
      setTools(await listarCatalogo())
    } catch {
      setErro(true)
    }
  }, [])

  useEffect(() => {
    void carregar()
  }, [carregar])

  async function alternar(nome: string, ativa: boolean) {
    setTools((ts) => ts?.map((t) => (t.nome === nome ? { ...t, ativa_global: ativa } : t)) ?? ts)
    try {
      const nova = await alternarGlobal(nome, ativa)
      setTools((ts) => ts?.map((t) => (t.nome === nome ? nova : t)) ?? ts)
      toast.success(ativa ? `${nome} ligada em todas as conversas.` : `${nome} desligada em todas as conversas.`)
    } catch {
      toast.error('Não foi possível alterar a tool. Tente de novo.')
      void carregar()
    }
  }

  return (
    <div className="mx-auto h-full max-w-3xl space-y-6 overflow-y-auto px-4 py-8">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">Tools</h1>
        <p className="text-sm text-muted-foreground">
          Desligar aqui vale para todas as conversas. Cada conversa ainda pode desligar a sua no painel lateral.
        </p>
      </div>
      {erro ? (
        <EstadoErro mensagem="Não foi possível carregar as tools." onTentarDeNovo={carregar} />
      ) : !tools ? (
        <EstadoCarregando />
      ) : tools.length === 0 ? (
        <EstadoVazio titulo="Nenhuma tool cadastrada" descricao="As tools nativas aparecem aqui depois da migração." />
      ) : (
        <div className="space-y-4">
          {tools.map((t) => (
            <Card key={t.nome}>
              <CardHeader className="flex flex-row items-start justify-between gap-4">
                <div className="min-w-0 space-y-1.5">
                  <CardTitle className="flex items-center gap-2 font-mono text-base">
                    {t.nome}
                    <Badge variant="secondary">{t.origem === 'mcp' ? 'MCP' : 'nativa'}</Badge>
                  </CardTitle>
                  <CardDescription>{t.descricao}</CardDescription>
                </div>
                <div className="flex shrink-0 items-center gap-2">
                  <Label htmlFor={`global-${t.nome}`} className="text-sm text-muted-foreground">
                    {t.ativa_global ? 'Ligada' : 'Desligada'}
                  </Label>
                  <Switch
                    id={`global-${t.nome}`}
                    checked={t.ativa_global}
                    onCheckedChange={(v) => void alternar(t.nome, v)}
                  />
                </div>
              </CardHeader>
              <CardContent>
                <Collapsible>
                  <CollapsibleTrigger className="group flex items-center gap-1 text-xs text-muted-foreground hover:text-foreground">
                    <ChevronDownIcon className="size-3.5 transition-transform group-data-[state=open]:rotate-180" />
                    Ver schema
                  </CollapsibleTrigger>
                  <CollapsibleContent className="mt-3 overflow-hidden rounded-md bg-muted/50">
                    <CodeBlock code={JSON.stringify(t.schema, null, 2)} language="json" />
                  </CollapsibleContent>
                </Collapsible>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
