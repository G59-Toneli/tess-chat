import { useState, type FormEvent } from 'react'
import { Navigate, useNavigate } from 'react-router'
import { UserRoundIcon } from 'lucide-react'
import { IconeApp, NOME_APP } from '@/components/Logo'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardFooter, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Spinner } from '@/components/ui/spinner'
import { cadastrar, CONTA_DEMO, entrar, lerToken, textoErroAuth } from '@/lib/api'

/** Login e cadastro no mesmo card. Conta demo preenche as credenciais. */
export function Login() {
  const navigate = useNavigate()
  const [modo, setModo] = useState<'entrar' | 'cadastrar'>('entrar')
  const [email, setEmail] = useState('')
  const [senha, setSenha] = useState('')
  const [erro, setErro] = useState<string | null>(null)
  const [enviando, setEnviando] = useState(false)

  if (lerToken()) return <Navigate to="/" replace />

  const cadastro = modo === 'cadastrar'

  async function enviar(e: FormEvent) {
    e.preventDefault()
    setErro(null)
    setEnviando(true)
    try {
      await (cadastro ? cadastrar : entrar)(email, senha)
      navigate('/', { replace: true })
    } catch (err) {
      setErro(textoErroAuth(err))
    } finally {
      setEnviando(false)
    }
  }

  function usarDemo() {
    setModo('entrar')
    setEmail(CONTA_DEMO.email)
    setSenha(CONTA_DEMO.senha)
    setErro(null)
  }

  return (
    <div className="flex min-h-dvh items-center justify-center bg-muted/30 p-4">
      <Card className="w-full max-w-sm">
        <CardHeader className="items-center text-center">
          <IconeApp className="mx-auto mb-2 size-10" />
          <CardTitle className="text-xl">{NOME_APP}</CardTitle>
          <CardDescription>
            {cadastro ? 'Crie sua conta para começar a conversar.' : 'Entre para continuar suas conversas.'}
          </CardDescription>
        </CardHeader>
        <form onSubmit={enviar}>
          <CardContent className="flex flex-col gap-4">
            <div className="flex flex-col gap-2">
              <Label htmlFor="email">E-mail</Label>
              <Input
                id="email"
                type="email"
                autoComplete="email"
                placeholder="voce@exemplo.com"
                required
                value={email}
                onChange={(e) => setEmail(e.target.value)}
              />
            </div>
            <div className="flex flex-col gap-2">
              <Label htmlFor="senha">Senha</Label>
              <Input
                id="senha"
                type="password"
                autoComplete={cadastro ? 'new-password' : 'current-password'}
                required
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
              />
            </div>
            {erro && (
              <p role="alert" className="text-sm text-destructive">
                {erro}
              </p>
            )}
          </CardContent>
          <CardFooter className="mt-4 flex flex-col gap-3">
            <Button type="submit" className="w-full" disabled={enviando}>
              {enviando && <Spinner />} {cadastro ? 'Criar conta' : 'Entrar'}
            </Button>
            {!cadastro && (
              <Button type="button" variant="outline" className="w-full" onClick={usarDemo}>
                <UserRoundIcon /> Entrar com conta demo
              </Button>
            )}
            <p className="text-sm text-muted-foreground">
              {cadastro ? 'Já tem conta?' : 'Não tem conta?'}{' '}
              <button
                type="button"
                className="font-medium text-foreground underline-offset-4 hover:underline"
                onClick={() => {
                  setModo(cadastro ? 'entrar' : 'cadastrar')
                  setErro(null)
                }}
              >
                {cadastro ? 'Entrar' : 'Criar conta'}
              </button>
            </p>
          </CardFooter>
        </form>
      </Card>
    </div>
  )
}
