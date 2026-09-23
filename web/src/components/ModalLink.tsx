import type { LinkSafetyModalProps } from 'streamdown'
import { Button } from '@/components/ui/button'
import {
  Dialog,
  DialogContent,
  DialogDescription,
  DialogFooter,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog'

/** Confirmação antes de abrir link externo da resposta. Substitui o modal padrão do Streamdown. */
export function ModalLink({ isOpen, onClose, onConfirm, url }: LinkSafetyModalProps) {
  return (
    <Dialog open={isOpen} onOpenChange={(aberto) => !aberto && onClose()}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Abrir link externo?</DialogTitle>
          <DialogDescription>Você vai sair do chat para este endereço:</DialogDescription>
        </DialogHeader>
        <p className="truncate rounded-md bg-muted px-3 py-2 font-mono text-sm" title={url}>
          {url}
        </p>
        <DialogFooter>
          <Button variant="outline" onClick={onClose}>
            Cancelar
          </Button>
          <Button
            onClick={() => {
              onConfirm()
              onClose()
            }}
          >
            Abrir
          </Button>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  )
}
