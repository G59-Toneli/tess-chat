import { useEffect, useState, type ReactNode } from 'react'
import type { FileUIPart } from 'ai'
import { FileTextIcon, PaperclipIcon, XIcon } from 'lucide-react'
import { Dialog as DialogPrimitive } from 'radix-ui'
import { PromptInputButton, PromptInputHeader, usePromptInputAttachments } from '@/components/ai-elements/prompt-input'
import { Button } from '@/components/ui/button'
import { Dialog, DialogClose, DialogOverlay, DialogPortal, DialogTitle, DialogTrigger } from '@/components/ui/dialog'
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
// Rota do link público (/api/s/...) não pede login: vai direto no src.
function useSrc(url: string | null): string | undefined {
  const direto = url && (url.startsWith('data:') || url.startsWith('/api/s/') ? url : previews.get(url))
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

/** Anexo dentro da Mensagem: miniatura da imagem (clique amplia) ou chip do PDF. */
export function AnexoNaMensagem({ parte }: { parte: FileUIPart }) {
  const pdf = ehPdf(parte.mediaType)
  const src = useSrc(pdf ? null : parte.url)
  if (pdf) return <ChipPdf nome={parte.filename} className="bg-background" />
  const nome = parte.filename ?? 'Imagem anexada'
  return src ? (
    <Lightbox src={src} nome={nome}>
      <img src={src} alt={nome} className="max-h-64 max-w-full rounded-lg border object-contain" />
    </Lightbox>
  ) : (
    <div className="size-32 animate-pulse rounded-lg border bg-muted" aria-label="Carregando imagem" />
  )
}

/** Imagem grande num overlay. Esc, clique fora e o botão fecham (Radix Dialog). */
function Lightbox({ src, nome, children }: { src: string; nome: string; children: ReactNode }) {
  return (
    <Dialog>
      <DialogTrigger asChild>
        <button
          type="button"
          aria-label={`Ampliar ${nome}`}
          className="block w-fit max-w-full cursor-zoom-in rounded-lg focus-visible:ring-2 focus-visible:ring-ring focus-visible:outline-none"
        >
          {children}
        </button>
      </DialogTrigger>
      <DialogPortal>
        <DialogOverlay className="bg-black/80 motion-reduce:animate-none" />
        <DialogPrimitive.Content
          aria-describedby={undefined}
          className="fixed top-1/2 left-1/2 z-50 -translate-x-1/2 -translate-y-1/2 outline-none duration-150 data-open:animate-in data-open:fade-in-0 data-open:zoom-in-95 data-closed:animate-out data-closed:fade-out-0 data-closed:zoom-out-95 motion-reduce:animate-none"
        >
          <DialogTitle className="sr-only">{nome}</DialogTitle>
          <img src={src} alt={nome} className="max-h-[90dvh] max-w-[90vw] rounded-lg object-contain shadow-2xl" />
          {/* Dentro do Content: fora dele o Radix deixa o botão inerte. */}
          <DialogClose asChild>
            <Button variant="secondary" size="icon" aria-label="Fechar imagem" className="absolute top-2 right-2 rounded-full">
              <XIcon />
            </Button>
          </DialogClose>
        </DialogPrimitive.Content>
      </DialogPortal>
    </Dialog>
  )
}
