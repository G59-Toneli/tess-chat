import { useState } from 'react'
import { useParams } from 'react-router'
import { Conversation, ConversationContent, ConversationEmptyState } from '@/components/ai-elements/conversation'
import { Message, MessageContent, MessageResponse } from '@/components/ai-elements/message'
import {
  PromptInput,
  PromptInputBody,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
  type PromptInputMessage,
} from '@/components/ai-elements/prompt-input'
import { mensagensMock, type MensagemMock } from '@/mock'

/** Área de chat com Mensagens mock. O envio só ecoa localmente. */
export function Chat() {
  const { id } = useParams()
  return <ChatConversa key={id ?? 'nova'} inicial={id ? (mensagensMock[id] ?? []) : []} />
}

function ChatConversa({ inicial }: { inicial: MensagemMock[] }) {
  const [mensagens, setMensagens] = useState(inicial)

  function enviar({ text }: PromptInputMessage) {
    if (!text.trim()) return
    setMensagens((m) => [
      ...m,
      { id: crypto.randomUUID(), role: 'user', texto: text },
      { id: crypto.randomUUID(), role: 'assistant', texto: '_Resposta mock: a API ainda não está ligada._' },
    ])
  }

  return (
    <div className="mx-auto flex h-full max-w-3xl flex-col p-4">
      <Conversation className="flex-1">
        <ConversationContent>
          {mensagens.length === 0 ? (
            <ConversationEmptyState title="Nova conversa" description="Mande uma mensagem para começar." />
          ) : (
            mensagens.map((m) => (
              <Message from={m.role} key={m.id}>
                <MessageContent>
                  <MessageResponse>{m.texto}</MessageResponse>
                </MessageContent>
              </Message>
            ))
          )}
        </ConversationContent>
      </Conversation>
      <PromptInput onSubmit={enviar} className="mt-4">
        <PromptInputBody>
          <PromptInputTextarea placeholder="Digite sua mensagem..." />
        </PromptInputBody>
        <PromptInputFooter>
          <span />
          <PromptInputSubmit />
        </PromptInputFooter>
      </PromptInput>
    </div>
  )
}
