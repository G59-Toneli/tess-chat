import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'
import { WrenchIcon } from 'lucide-react'
import { PromptInputButton } from '@/components/ai-elements/prompt-input'
import { Badge } from '@/components/ui/badge'
import { Label } from '@/components/ui/label'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { Skeleton } from '@/components/ui/skeleton'
import { Switch } from '@/components/ui/switch'
import { Button } from '@/components/ui/button'
import { alternarNaConversa, listarCatalogo, toolsDaConversa, type ToolConversa } from '@/lib/tools'

/** Botão da barra do input com contador de Tools ativas; abre popover com switches (GET/PUT /api/conversations/{id}/tools). */
export function SeletorTools({ conversaId }: { conversaId?: string }) {
  const [tools, setTools] = useState<ToolConversa[] | null>(null)
  const [globais, setGlobais] = useState<Map<string, boolean>>(new Map())
  const [erro, setErro] = useState(false)

  const carregar = useCallback(async () => {
    setErro(false)
    try {
      const [catalogo, daConversa] = await Promise.all([
        listarCatalogo(),
        conversaId ? toolsDaConversa(conversaId) : Promise.resolve(null),
      ])
      setGlobais(new Map(catalogo.map((t) => [t.nome, t.ativa_global])))
      setTools(daConversa ?? catalogo.map((t) => ({
          nome: t.nome,
          origem: t.origem,
          descricao_usuario: t.descricao_usuario,
          ativa: t.ativa_global,
        })),)
    } catch {
      setErro(true)
    }
  }, [conversaId])

  useEffect(() => {
    void carregar()
  }, [carregar])

  async function alternar(nome: string, ativa: boolean) {
    if (!conversaId) return
    setTools((ts) => ts?.map((t) => (t.nome === nome ? { ...t, ativa } : t)) ?? ts)
    try {
      setTools(await alternarNaConversa(conversaId, nome, ativa))
    } catch {
      toast.error('Não foi possível alterar a tool. Tente de novo.')
      void carregar()
    }
  }

  const ativas = tools?.filter((t) => t.ativa && (globais.get(t.nome) ?? true)).length

  return (
    <Popover>
      <PopoverTrigger asChild>
        <PromptInputButton aria-label="Tools da conversa">
          <WrenchIcon className="size-4" />
          <span>{ativas === undefined ? 'Tools' : `${ativas} ${ativas === 1 ? 'tool' : 'tools'}`}</span>
        </PromptInputButton>
      </PopoverTrigger>
      <PopoverContent align="start" side="top" className="w-80 gap-3 p-4" aria-label="Tools da conversa">
        <div className="flex items-center gap-2 text-sm font-semibold">
          <WrenchIcon className="size-4 text-muted-foreground" /> Tools da conversa
        </div>
        {erro ? (
          <div className="space-y-2 text-sm text-muted-foreground">
            <p>Não foi possível carregar as tools.</p>
            <Button variant="outline" size="sm" onClick={carregar}>
              Tentar de novo
            </Button>
          </div>
        ) : !tools ? (
          <div className="space-y-3" role="status" aria-label="Carregando tools">
            <Skeleton className="h-10 w-full" />
            <Skeleton className="h-10 w-full" />
          </div>
        ) : tools.length === 0 ? (
          <p className="text-sm text-muted-foreground">Nenhuma tool cadastrada.</p>
        ) : (
          <ul className="-mr-4 max-h-80 space-y-4 overflow-y-auto pr-4">
            {tools.map((t) => {
              const global = globais.get(t.nome) ?? true
              const id = `tool-${t.nome}`
              return (
                <li key={t.nome} className="space-y-1">
                  <div className="flex items-center justify-between gap-3">
                    <Label htmlFor={id} className="min-w-0 font-mono text-sm">
                      <span className="truncate" title={t.nome}>
                        {t.nome}
                      </span>
                      {(t.origem === 'mcp' || t.origem === 'api') && (
                        <Badge variant="outline" className="shrink-0 font-sans" title={t.servidor ?? undefined}>
                          {t.origem}
                        </Badge>
                      )}
                    </Label>
                    <Switch
                      id={id}
                      checked={t.ativa}
                      disabled={!conversaId || !global}
                      onCheckedChange={(v) => void alternar(t.nome, v)}
                    />
                  </div>
                  <p className="line-clamp-2 text-xs text-muted-foreground">
                    {!global
                      ? 'Desligada para todas as conversas.'
                      : t.servidor
                        ? `${t.servidor} · ${t.descricao_usuario}`
                        : t.descricao_usuario}
                  </p>
                </li>
              )
            })}
          </ul>
        )}
        {!conversaId && tools && (
          <p className="text-xs text-muted-foreground">Envie a primeira mensagem para ajustar as tools desta conversa.</p>
        )}
        <Link to="/tools" className="border-t pt-3 text-xs text-muted-foreground underline-offset-4 hover:underline">
          Gerenciar tools
        </Link>
      </PopoverContent>
    </Popover>
  )
}
