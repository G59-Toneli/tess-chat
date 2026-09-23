import { useNavigate } from 'react-router'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

/** Login placeholder: não autentica, só navega para `/`. */
export function Login() {
  const navigate = useNavigate()
  return (
    <div className="flex h-dvh items-center justify-center">
      <form
        className="flex w-80 flex-col gap-3"
        onSubmit={(e) => {
          e.preventDefault()
          navigate('/')
        }}
      >
        <h1 className="text-2xl font-semibold">Entrar</h1>
        <Input type="email" placeholder="E-mail" />
        <Input type="password" placeholder="Senha" />
        <Button type="submit">Entrar</Button>
      </form>
    </div>
  )
}
