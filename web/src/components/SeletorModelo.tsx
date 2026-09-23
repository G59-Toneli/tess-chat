import { useCallback, useEffect, useId, useState } from 'react'
import { Link } from 'react-router'
import { toast } from 'sonner'
import { CheckIcon, ChevronDownIcon } from 'lucide-react'
import { LayoutGroup, motion } from 'motion/react'
import { PromptInputButton } from '@/components/ai-elements/prompt-input'
import { Popover, PopoverContent, PopoverTrigger } from '@/components/ui/popover'
import { cn } from '@/lib/utils'
import { MODELOS, NIVEIS, lerConfig, salvarConfig, type Configuracao } from '@/lib/configuracao'

export type EscolhaModelo = Partial<Pick<Configuracao, 'modelo' | 'nivel_raciocinio'>>

const CURTO: Record<string, string> = {
  'gemini-3.8-flash': '3.8 Flash',
  'gemini-3.1-flash-lite': 'Flash-Lite',
}
const TAG: Record<string, string> = {
  'gemini-3.8-flash': 'Padrão',
  'gemini-3.1-flash-lite': 'Mais barato',
}

type Item = { valor: string; rotulo: string; tag?: string }

/** Lista com um destaque só que desliza até o item sob o mouse (layoutId do motion). */
function Lista({ titulo, itens, atual, onEscolher }: { titulo: string; itens: Item[]; atual?: string; onEscolher: (v: string) => void }) {
  const [sob, setSob] = useState<string | null>(null)
  const grupo = useId()
  return (
    <div role="group" aria-label={titulo}>
      <p className="px-2 pt-1 pb-1.5 text-xs text-muted-foreground">{titulo}</p>
      <LayoutGroup id={grupo}>
        <ul onMouseLeave={() => setSob(null)}>
          {itens.map((i) => (
            <li key={i.valor} className="relative">
              {sob === i.valor && (
                <motion.span
                  layoutId="destaque"
                  aria-hidden
                  className="absolute inset-0 rounded-md bg-accent"
                  transition={{ type: 'spring', duration: 0.25, bounce: 0 }}
                />
              )}
              <button
                type="button"
                role="menuitemradio"
                aria-checked={i.valor === atual}
                onMouseEnter={() => setSob(i.valor)}
                onFocus={() => setSob(i.valor)}
                onClick={() => onEscolher(i.valor)}
                className="relative flex h-8 w-full items-center gap-2 rounded-md px-2 text-left outline-none"
              >
                <span className="min-w-0 flex-1 truncate font-medium">{i.rotulo}</span>
                {i.tag && <span className="shrink-0 text-xs text-muted-foreground">{i.tag}</span>}
                <CheckIcon className={cn('size-3.5 shrink-0', i.valor !== atual && 'invisible')} />
              </button>
            </li>
          ))}
        </ul>
      </LayoutGroup>
    </div>
  )
}

/**
 * Modelo e nível de raciocínio na barra do input. Com Conversa, grava direto no settings dela.
 * Sem Conversa ("/"), só devolve a escolha por `onEscolha`: quem cria a Conversa aplica antes do envio.
 */
export function SeletorModelo({
  conversaId,
  escolha,
  onEscolha,
}: {
  conversaId?: string
  escolha?: EscolhaModelo
  onEscolha?: (e: EscolhaModelo) => void
}) {
  const [efetiva, setEfetiva] = useState<Configuracao | null>(null)
  const [aberto, setAberto] = useState(false)

  const carregar = useCallback(async () => {
    try {
      setEfetiva((await lerConfig(conversaId ?? null)).efetiva)
    } catch {
      setEfetiva(null)
    }
  }, [conversaId])

  useEffect(() => void carregar(), [carregar])

  const atual = efetiva && { ...efetiva, ...escolha }

  async function escolher(mudanca: EscolhaModelo) {
    if (!conversaId) {
      onEscolha?.({ ...escolha, ...mudanca })
      return
    }
    const antes = efetiva
    setEfetiva((e) => e && { ...e, ...mudanca })
    try {
      setEfetiva((await salvarConfig(conversaId, mudanca)).efetiva)
    } catch {
      setEfetiva(antes)
      toast.error('Não foi possível trocar. Tente de novo.')
    }
  }

  const nivel = NIVEIS.find((n) => n.valor === atual?.nivel_raciocinio)?.rotulo

  return (
    <Popover open={aberto} onOpenChange={setAberto}>
      <PopoverTrigger asChild>
        <PromptInputButton aria-label="Modelo e raciocínio" disabled={!atual}>
          <span>{atual ? `${CURTO[atual.modelo] ?? atual.modelo} · ${nivel ?? atual.nivel_raciocinio}` : 'Modelo'}</span>
          <ChevronDownIcon className="size-3 text-muted-foreground" />
        </PromptInputButton>
      </PopoverTrigger>
      <PopoverContent align="start" side="top" className="w-60 gap-1 p-1" role="menu" aria-label="Modelo e raciocínio">
        <Lista
          titulo="Modelo"
          itens={MODELOS.map((m) => ({ valor: m.valor, rotulo: `Gemini ${CURTO[m.valor] ?? m.rotulo}`, tag: TAG[m.valor] }))}
          atual={atual?.modelo}
          onEscolher={(modelo) => void escolher({ modelo })}
        />
        <div className="mx-1 border-t" />
        <Lista
          titulo="Raciocínio"
          itens={NIVEIS}
          atual={atual?.nivel_raciocinio}
          onEscolher={(nivel_raciocinio) => void escolher({ nivel_raciocinio })}
        />
        <Link
          to={conversaId ? `/config?conversa=${conversaId}` : '/config'}
          onClick={() => setAberto(false)}
          className="mx-1 mt-1 border-t px-1 pt-2 pb-1 text-xs text-muted-foreground underline-offset-4 hover:underline"
        >
          Mais opções
        </Link>
      </PopoverContent>
    </Popover>
  )
}
