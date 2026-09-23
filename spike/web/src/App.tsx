import { useChat } from '@ai-sdk/react'
import { DefaultChatTransport } from 'ai'
import { Conversation, ConversationContent } from '@/components/ai-elements/conversation'
import { Message, MessageContent, MessageResponse } from '@/components/ai-elements/message'
import {
  PromptInput,
  PromptInputBody,
  PromptInputFooter,
  PromptInputSubmit,
  PromptInputTextarea,
  type PromptInputMessage,
} from '@/components/ai-elements/prompt-input'

export default function App() {
  const { messages, sendMessage, status } = useChat({
    transport: new DefaultChatTransport({ api: '/api/chat' }),
  })

  const onSubmit = (m: PromptInputMessage) => {
    if (m.text) sendMessage({ text: m.text })
  }

  return (
    <div className="mx-auto flex h-screen max-w-2xl flex-col p-4">
      <Conversation className="flex-1">
        <ConversationContent>
          {messages.map((msg) => (
            <Message from={msg.role} key={msg.id}>
              <MessageContent>
                {msg.parts.map((p, i) =>
                  p.type === 'text' ? <MessageResponse key={i}>{p.text}</MessageResponse> : null,
                )}
              </MessageContent>
            </Message>
          ))}
        </ConversationContent>
      </Conversation>
      <PromptInput onSubmit={onSubmit}>
        <PromptInputBody>
          <PromptInputTextarea />
        </PromptInputBody>
        <PromptInputFooter>
          <PromptInputSubmit status={status} />
        </PromptInputFooter>
      </PromptInput>
    </div>
  )
}
