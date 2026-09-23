import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router'
import { PencilIcon, ShieldAlertIcon } from 'lucide-react'
import { toast } from 'sonner'
import { EstadoCarregando, EstadoErro, EstadoVazio } from '@/components/estados'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Switch } from '@/components/ui/switch'
import { Empty, EmptyDescription, EmptyHeader, EmptyMedia, EmptyTitle } from '@/components/ui/empty'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useContextoApp } from '@/layout/AppLayout'
import { configPublica } from '@/lib/api'
import { definirCap, salvarCadastroAberto } from '@/lib/configuracao'
import { painelCredito, usd, usuariosAdmin, type Saldo, type UsuarioAdmin } from '@/lib/painel'
import { Resumo } from '@/pages/Creditos'

/** Só admin: Cap global, gasto total e Usuários com gasto e Cap. */
export function Admin() {
  const { usuario } = useContextoApp()
  if (usuario === null) return <div className="mx-auto max-w-6xl p-8"><EstadoCarregando /></div>
  if (!usuario.is_superuser) return <AcessoRestrito />
  return <PainelAdmin />
}

function PainelAdmin() {
  const [dados, setDados] = useState<{ saldo: Saldo; usuarios: UsuarioAdmin[] } | null>(null)
  const [erro, setErro] = useState(false)
  const [editando, setEditando] = useState<UsuarioAdmin | null>(null)

  const carregar = useCallback(async () => {
    setErro(false)
    setDados(null)
    try {
      const [painel, usuarios] = await Promise.all([painelCredito('global'), usuariosAdmin()])
      setDados({ saldo: painel.saldo, usuarios })
    } catch {
      setErro(true)
    }
  }, [])

  useEffect(() => void carregar(), [carregar])

  return (
    <div className="mx-auto max-w-6xl p-8">
      <h1 className="text-2xl font-semibold">Administração</h1>
      <p className="mt-1 mb-6 text-sm text-muted-foreground">Cap global, gasto total e gasto de cada Usuário.</p>
      {erro ? (
        <EstadoErro mensagem="Não foi possível carregar os dados de administração." onTentarDeNovo={carregar} />
      ) : dados === null ? (
        <EstadoCarregando />
      ) : (
        <div className="flex flex-col gap-6">
          <Resumo saldo={dados.saldo} global />
          <CardCadastro />
          <Card>
            <CardHeader>
              <CardTitle>Usuários</CardTitle>
              <CardDescription>{dados.usuarios.length} contas, do maior gasto para o menor.</CardDescription>
            </CardHeader>
            <CardContent>
              {dados.usuarios.length === 0 ? (
                <EstadoVazio titulo="Nenhum usuário" descricao="As contas cadastradas aparecem aqui." />
              ) : (
                <Table>
                  <TableHeader>
                    <TableRow>
                      <TableHead>E-mail</TableHead>
                      <TableHead className="text-right">Gasto</TableHead>
                      <TableHead className="text-right">Cap</TableHead>
                      <TableHead className="text-right">Uso</TableHead>
                      <TableHead className="w-0" />
                    </TableRow>
                  </TableHeader>
                  <TableBody>
                    {dados.usuarios.map((u) => (
                      <TableRow key={u.id}>
                        <TableCell className="max-w-80">
                          <div className="flex items-center gap-2">
                            <span className="truncate">{u.email}</span>
                            {u.is_superuser && <Badge variant="outline">admin</Badge>}
                          </div>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">{usd(u.gasto_micro_usd)}</TableCell>
                        <TableCell className="text-right tabular-nums">
                          <Button
                            variant="ghost"
                            size="sm"
                            className="tabular-nums"
                            aria-label={`Editar Cap de ${u.email}`}
                            onClick={() => setEditando(u)}
                          >
                            {usd(u.cap_micro_usd)} <PencilIcon />
                          </Button>
                        </TableCell>
                        <TableCell className="text-right tabular-nums">
                          {((u.gasto_micro_usd / Math.max(1, u.cap_micro_usd)) * 100).toLocaleString('pt-BR', {
                            maximumFractionDigits: 1,
                          })}
                          %
                        </TableCell>
                        <TableCell>
                          <Button variant="ghost" size="sm" asChild>
                            <Link to={`/auditoria?usuario=${u.id}`}>Ver eventos</Link>
                          </Button>
                        </TableCell>
                      </TableRow>
                    ))}
                  </TableBody>
                </Table>
              )}
            </CardContent>
          </Card>
        </div>
      )}
      <DialogCap usuario={editando} fechar={() => setEditando(null)} recarregar={carregar} />
    </div>
  )
}

/** Toggle global do cadastro. Fechado, /auth/register responde 403 e o Login esconde "Criar conta". */
function CardCadastro() {
  const [aberto, setAberto] = useState<boolean | null>(null)

  useEffect(() => {
    configPublica()
      .then((c) => setAberto(c.cadastro_aberto))
      .catch(() => setAberto(null))
  }, [])

  async function alternar(v: boolean) {
    setAberto(v)
    try {
      setAberto((await salvarCadastroAberto(v)).cadastro_aberto)
      toast.success(v ? 'Cadastro aberto.' : 'Cadastro fechado. Só contas existentes entram.')
    } catch {
      setAberto(!v)
      toast.error('Não foi possível alterar o cadastro. Tente de novo.')
    }
  }

  return (
    <Card>
      <CardHeader className="flex flex-row items-start justify-between gap-4">
        <div className="min-w-0 space-y-1.5">
          <CardTitle>Cadastro</CardTitle>
          <CardDescription>Aberto, qualquer pessoa cria conta na tela de login. Fechado, só contas existentes entram.</CardDescription>
        </div>
        <div className="flex shrink-0 items-center gap-2">
          <Label htmlFor="cadastro-aberto" className="text-sm text-muted-foreground">
            {aberto ? 'Aberto' : 'Fechado'}
          </Label>
          <Switch
            id="cadastro-aberto"
            checked={aberto ?? false}
            disabled={aberto === null}
            onCheckedChange={(v) => void alternar(v)}
          />
        </div>
      </CardHeader>
    </Card>
  )
}

/** Cap do Usuário em US$. A API grava em micro-USD e emite settings_changed. */
function DialogCap({
  usuario,
  fechar,
  recarregar,
}: {
  usuario: UsuarioAdmin | null
  fechar: () => void
  recarregar: () => Promise<void>
}) {
  const [valor, setValor] = useState('')
  useEffect(() => setValor(usuario ? (usuario.cap_micro_usd / 1_000_000).toString().replace('.', ',') : ''), [usuario])
  const micro = Math.round(Number(valor.replace(',', '.')) * 1_000_000)
  const valido = valor.trim() !== '' && Number.isFinite(micro) && micro >= 0

  async function salvar(e: FormEvent) {
    e.preventDefault()
    if (!usuario || !valido) return
    try {
      await definirCap(usuario.id, micro)
      toast.success(`Cap de ${usuario.email} agora é ${usd(micro)}.`)
      fechar()
      await recarregar()
    } catch {
      toast.error('Não foi possível salvar o Cap. Tente de novo.')
    }
  }

  return (
    <Dialog open={usuario !== null} onOpenChange={(aberto) => !aberto && fechar()}>
      <DialogContent>
        <form onSubmit={salvar} className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>Cap de crédito</DialogTitle>
            <DialogDescription className="truncate">{usuario?.email}</DialogDescription>
          </DialogHeader>
          <div className="flex flex-col gap-2">
            <Label htmlFor="cap">Limite em US$</Label>
            <Input
              id="cap"
              inputMode="decimal"
              value={valor}
              onChange={(e) => setValor(e.target.value.replace(/[^\d.,]/g, ''))}
              autoFocus
            />
          </div>
          <DialogFooter>
            <Button type="button" variant="outline" onClick={fechar}>
              Cancelar
            </Button>
            <Button type="submit" disabled={!valido}>
              Salvar
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function AcessoRestrito() {
  return (
    <div className="mx-auto max-w-6xl p-8">
      <h1 className="mb-6 text-2xl font-semibold">Administração</h1>
      <Empty>
        <EmptyHeader>
          <EmptyMedia variant="icon">
            <ShieldAlertIcon />
          </EmptyMedia>
          <EmptyTitle>Acesso restrito</EmptyTitle>
          <EmptyDescription>Esta tela é só para a conta de administração.</EmptyDescription>
        </EmptyHeader>
        <Button variant="outline" asChild>
          <Link to="/creditos">Ver meu crédito</Link>
        </Button>
      </Empty>
    </div>
  )
}
