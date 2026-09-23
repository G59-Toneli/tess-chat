import { useEffect, useState } from 'react'
import type { FileUIPart } from 'ai'
import { FileTextIcon, PaperclipIcon, XIcon } from 'lucide-react'
import { PromptInputButton, PromptInputHeader, usePromptInputAttachments } from '@/components/ai-elements/prompt-input'
import { authHeader } from '@/lib/api'
import { cn } from '@/lib/utils'

// Data URL de cada anexo enviado nesta aba, pela URL da API. Evita baixar de novo o que acabou de subir.
export const previews = new Map<string, string>()

const ehPdf = (mediaType: string) => mediaType === 'application/pdf'

export function BotaoAnexar() {
  const anexos = usePromptInputAttachments()
  return (
    <PromptInputButton tooltip="Anexar imagem ou PDF" aria-label="Anexar imagem ou PDF" onClick={anexos.openFileDialog}>
      <PaperclipIcon className="size-4" />
    </PromptInputButton>
  )
}

/** Anexos escolhidos e ainda não enviados, acima do campo de texto. */
export function AnexosDoPrompt() {
  const anexos = usePromptInputAttachments()
  if (anexos.files.length === 0) return null
  return (
    <PromptInputHeader className="px-3 pt-3">
      {anexos.files.map((f) => (
        <div key={f.id} className="group relative">
          {ehPdf(f.mediaType) ? (
            <ChipPdf nome={f.filename} />
          ) : (
            <img src={f.url} alt={f.filename ?? 'Imagem anexada'} className="size-14 rounded-md border object-cover" />
          )}
          <button
            type="button"
            onClick={() => anexos.remove(f.id)}
            aria-label={`Remover ${f.filename ?? 'anexo'}`}
            className="absolute -top-1.5 -right-1.5 flex size-5 items-center justify-center rounded-full border bg-background text-muted-foreground shadow-sm hover:text-foreground focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
          >
            <XIcon className="size-3" />
          </button>
        </div>
      ))}
    </PromptInputHeader>
  )
}

function ChipPdf({ nome, className }: { nome?: string; className?: string }) {
  return (
    <div className={cn('flex h-14 max-w-56 items-center gap-2 rounded-md border bg-muted/50 px-3', className)}>
      <FileTextIcon className="size-5 shrink-0 text-muted-foreground" />
      <div className="min-w-0 text-left">
        <p className="truncate text-sm">{nome ?? 'Documento'}</p>
        <p className="text-xs text-muted-foreground">PDF</p>
      </div>
    </div>
  )
}

// Imagem da API precisa do header Bearer: <img src> não manda. Baixa como blob.
function useSrc(url: string | null): string | undefined {
  const direto = url && (url.startsWith('data:') ? url : previews.get(url))
  const [baixada, setBaixada] = useState<string>()
  useEffect(() => {
    if (!url || direto) return
    let objeto: string | undefined
    let vivo = true
    void fetch(url, { headers: authHeader() })
      .then((r) => (r.ok ? r.blob() : Promise.reject()))
      .then((b) => {
        objeto = URL.createObjectURL(b)
        if (vivo) setBaixada(objeto)
      })
      .catch(() => {})
    return () => {
      vivo = false
      if (objeto) URL.revokeObjectURL(objeto)
    }
  }, [url, direto])
  return direto || baixada
}

/** Anexo dentro da Mensagem: miniatura da imagem ou chip do PDF. */
export function AnexoNaMensagem({ parte }: { parte: FileUIPart }) {
  const pdf = ehPdf(parte.mediaType)
  const src = useSrc(pdf ? null : parte.url)
  if (pdf) return <ChipPdf nome={parte.filename} className="bg-background" />
  return src ? (
    <img src={src} alt={parte.filename ?? 'Imagem anexada'} className="max-h-64 max-w-full rounded-lg border object-contain" />
  ) : (
    <div className="size-32 animate-pulse rounded-lg border bg-muted" aria-label="Carregando imagem" />
  )
}
