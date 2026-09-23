import { Share2Icon } from 'lucide-react'
import { toast } from 'sonner'
import { DropdownMenuItem } from '@/components/ui/dropdown-menu'
import type { Conversa } from '@/lib/api'
import { copiar, criarShare, urlAbsoluta } from '@/lib/shares'

// Toast em vez de dialog: o conteúdo do DropdownMenu desmonta quando o menu fecha.
async function compartilhar(conversa: Conversa) {
  try {
    const url = urlAbsoluta(await criarShare(conversa.id))
    const copiou = await copiar(url)
    toast.success(copiou ? 'Link copiado' : 'Link criado', {
      description: (
        <>
          <span className="block break-all font-mono text-xs">{url}</span>
          Mensagens enviadas depois não aparecem no link. Revogue em Compartilhados.
        </>
      ),
      duration: 10000,
      action: { label: 'Copiar', onClick: () => void copiar(url) },
    })
  } catch {
    toast.error('Não foi possível criar o link.')
  }
}

/** Item "Compartilhar" do menu da Conversa. */
export function ItemCompartilhar({ conversa }: { conversa: Conversa }) {
  return (
    <DropdownMenuItem onSelect={() => void compartilhar(conversa)}>
      <Share2Icon /> Compartilhar
    </DropdownMenuItem>
  )
}
