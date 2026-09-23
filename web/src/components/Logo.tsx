import { SparklesIcon } from 'lucide-react'
import { cn } from '@/lib/utils'

export const NOME_APP = 'Tess Chat'

/** Ícone do app: quadrado arredondado na cor primária. */
export function IconeApp({ className }: { className?: string }) {
  return (
    <span
      className={cn('flex size-8 shrink-0 items-center justify-center rounded-lg bg-primary text-primary-foreground', className)}
    >
      <SparklesIcon className="size-4" />
    </span>
  )
}
