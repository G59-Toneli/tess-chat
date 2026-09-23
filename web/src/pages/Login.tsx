import { useState } from 'react'
import { useNavigate } from 'react-router'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'

/** Login e cadastro placeholder: não autentica, só navega para `/`. */
export function Login() {
  const navigate = useNavigate()
  const [cadastro, setCadastro] = useState(false)
  return (
    <div className="flex h-dvh items-center justify-center">
      <form
        className="flex w-80 flex-col gap-3"
        onSubmit={(e) => {
          e.preventDefault()
          navigate('/')
        }}
      >
        <h1 className="text-2xl font-semibold">{cadastro ? 'Criar conta' : 'Entrar'}</h1>
        <label className="text-sm" htmlFor="email">E-mail</label>
        <Input id="email" type="email" placeholder="voce@exemplo.com" />
        <label className="text-sm" htmlFor="senha">Senha</label>
        <Input id="senha" type="password" />
        <Button type="submit">{cadastro ? 'Criar conta' : 'Entrar'}</Button>
        <Button type="button" variant="link" onClick={() => setCadastro((c) => !c)}>
          {cadastro ? 'Já tenho conta' : 'Criar uma conta'}
        </Button>
        <div className="rounded-md border p-3 text-sm">
          <p className="font-medium">Conta demo</p>
          <p className="text-muted-foreground">Entre sem cadastro para testar.</p>
          <Button type="submit" variant="secondary" size="sm" className="mt-2 w-full">
            Entrar com a conta demo
          </Button>
        </div>
      </form>
    </div>
  )
}
