import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link, Navigate, NavLink, Outlet, useLocation, useMatch, useNavigate, useOutletContext } from 'react-router'
import { toast } from 'sonner'
import {
  CoinsIcon,
  GlobeIcon,
  LogOutIcon,
  MoonIcon,
  MoreHorizontalIcon,
  PencilIcon,
  PlugIcon,
  PlusIcon,
  ScrollTextIcon,
  SearchIcon,
  ServerIcon,
  Share2Icon,
  ShieldIcon,
  SlidersHorizontalIcon,
  SunIcon,
  Trash2Icon,
  WrenchIcon,
  type LucideIcon,
} from 'lucide-react'
import { IconeApp, NOME_APP } from '@/components/Logo'
import { ItemCompartilhar } from '@/components/ItemCompartilhar'
import {
  AlertDialog,
  AlertDialogAction,
  AlertDialogCancel,
  AlertDialogContent,
  AlertDialogDescription,
  AlertDialogFooter,
  AlertDialogHeader,
  AlertDialogTitle,
} from '@/components/ui/alert-dialog'
import { Avatar, AvatarFallback } from '@/components/ui/avatar'
import { Button } from '@/components/ui/button'
import { Dialog, DialogContent, DialogFooter, DialogHeader, DialogTitle } from '@/components/ui/dialog'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { Input } from '@/components/ui/input'
import {
  SidebarGroup,
  SidebarGroupContent,
  SidebarGroupLabel,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarProvider,
} from '@/components/ui/sidebar'
import { Skeleton } from '@/components/ui/skeleton'
import {
  apagarConversa,
  eu,
  lerToken,
  listarConversas,
  renomearConversa,
  sair,
  type Conversa,
  type Usuario,
} from '@/lib/api'
import { agruparPorData, iniciais } from '@/lib/datas'
import { cn } from '@/lib/utils'
import { alternarTema, temaEscuro } from '@/tema'

type ItemNav = { to: string; rotulo: string; icone: LucideIcon; soAdmin?: boolean }

// Telas internas no rodapé da sidebar (ticket 28). /perfil fica fora até existir: hoje é placeholder.
const gruposNav: { rotulo: string; itens: ItemNav[] }[] = [
  {
    rotulo: 'Extensões',
    itens: [
      { to: '/tools', rotulo: 'Tools', icone: WrenchIcon },
      { to: '/api-tools', rotulo: 'Tools por API', icone: GlobeIcon },
      { to: '/mcp', rotulo: 'Servidores MCP', icone: ServerIcon },
      { to: '/conectores', rotulo: 'Conectores', icone: PlugIcon },
    ],
  },
  {
    rotulo: 'Conta',
    itens: [
      { to: '/config', rotulo: 'Configuração', icone: SlidersHorizontalIcon },
      { to: '/creditos', rotulo: 'Créditos', icone: CoinsIcon },
      { to: '/compartilhados', rotulo: 'Compartilhados', icone: Share2Icon },
      { to: '/auditoria', rotulo: 'Auditoria', icone: ScrollTextIcon },
      { to: '/admin', rotulo: 'Administração', icone: ShieldIcon, soAdmin: true },
    ],
  },
]

export type ContextoApp = {
  usuario: Usuario | null
  conversas: Conversa[] | null
  recarregarConversas: () => Promise<void>
}

export const useContextoApp = () => useOutletContext<ContextoApp>()

/** Layout autenticado: sidebar de Conversas, header com menu do Usuário, conteúdo. */
export function AppLayout() {
  if (!lerToken()) return <Navigate to="/login" replace />
  return <LayoutAutenticado />
}

function LayoutAutenticado() {
  const navigate = useNavigate()
  const [usuario, setUsuario] = useState<Usuario | null>(null)
  const [conversas, setConversas] = useState<Conversa[] | null>(null)
  const [erroConversas, setErroConversas] = useState(false)

  const recarregarConversas = useCallback(async () => {
    try {
      setConversas(await listarConversas())
      setErroConversas(false)
    } catch {
      // Falha no primeiro carregamento: a sidebar mostra o erro. Depois disso, a lista antiga fica.
      toast.error('Não foi possível carregar as conversas.')
      setErroConversas(true)
    }
  }, [])

  useEffect(() => {
    eu().then(setUsuario, () => undefined)
    void recarregarConversas()
  }, [recarregarConversas])

  const contexto = useMemo(
    () => ({ usuario, conversas, recarregarConversas }),
    [usuario, conversas, recarregarConversas],
  )

  return (
    <SidebarProvider className="h-svh overflow-hidden">
      <aside className="flex w-72 shrink-0 flex-col border-r bg-sidebar text-sidebar-foreground">
        <Link to="/" className="flex h-14 shrink-0 items-center gap-2 px-4 font-semibold">
          <IconeApp className="size-7" /> {NOME_APP}
        </Link>
        <SidebarConversas conversas={conversas} erro={erroConversas} recarregar={recarregarConversas} />
        <NavTelas admin={usuario?.is_superuser ?? false} />
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 shrink-0 items-center justify-end border-b px-4">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" className="gap-2 px-2" aria-label="Menu do usuário">
                <Avatar size="sm">
                  <AvatarFallback className="text-xs">{usuario ? iniciais(usuario.email) : '…'}</AvatarFallback>
                </Avatar>
                <span className="max-w-48 truncate text-sm">{usuario?.email}</span>
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-56">
              <DropdownMenuLabel className="truncate">{usuario?.email}</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={() => navigate('/config')}>
                <SlidersHorizontalIcon /> Configuração
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={alternarTema}>
                {temaEscuro() ? <SunIcon /> : <MoonIcon />} {temaEscuro() ? 'Tema claro' : 'Tema escuro'}
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={sair}>
                <LogOutIcon /> Sair
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>
        <main className="min-h-0 flex-1 overflow-y-auto">
          <Outlet context={contexto} />
        </main>
      </div>
    </SidebarProvider>
  )
}

/** Bloco fixo no rodapé da sidebar com as telas internas. Administração só para superuser. */
function NavTelas({ admin }: { admin: boolean }) {
  const { pathname } = useLocation()
  return (
    <nav aria-label="Telas" className="shrink-0 border-t border-sidebar-border py-1">
      {gruposNav.map((g) => (
        <SidebarGroup key={g.rotulo} className="py-1">
          <SidebarGroupLabel>{g.rotulo}</SidebarGroupLabel>
          <SidebarGroupContent>
            <SidebarMenu>
              {g.itens
                .filter((i) => admin || !i.soAdmin)
                .map((i) => (
                  <SidebarMenuItem key={i.to}>
                    <SidebarMenuButton asChild isActive={pathname.startsWith(i.to)}>
                      <NavLink to={i.to}>
                        <i.icone /> <span>{i.rotulo}</span>
                      </NavLink>
                    </SidebarMenuButton>
                  </SidebarMenuItem>
                ))}
            </SidebarMenu>
          </SidebarGroupContent>
        </SidebarGroup>
      ))}
    </nav>
  )
}

function SidebarConversas({
  conversas,
  erro,
  recarregar,
}: {
  conversas: Conversa[] | null
  erro: boolean
  recarregar: () => Promise<void>
}) {
  const [busca, setBusca] = useState('')
  const [renomeando, setRenomeando] = useState<Conversa | null>(null)
  const [apagando, setApagando] = useState<Conversa | null>(null)

  const grupos = useMemo(() => {
    const termo = busca.trim().toLowerCase()
    const filtradas = (conversas ?? []).filter((c) => c.title.toLowerCase().includes(termo))
    return agruparPorData(filtradas)
  }, [conversas, busca])

  return (
    <>
      <div className="flex flex-col gap-2 px-3 pb-3">
        <Button className="w-full justify-start" variant="outline" asChild>
          <Link to="/">
            <PlusIcon /> Nova conversa
          </Link>
        </Button>
        <div className="relative">
          <SearchIcon className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
          <Input
            aria-label="Buscar conversas"
            placeholder="Buscar conversas"
            className="pl-8"
            value={busca}
            onChange={(e) => setBusca(e.target.value)}
          />
        </div>
      </div>
      <nav className="flex-1 overflow-y-auto px-2 pb-3" aria-label="Conversas">
        {conversas === null && erro && (
          <div className="flex flex-col items-start gap-2 px-3 py-2 text-sm text-muted-foreground" role="alert">
            Não foi possível carregar as conversas.
            <Button variant="outline" size="sm" onClick={() => void recarregar()}>
              Tentar de novo
            </Button>
          </div>
        )}
        {conversas === null && !erro && (
          <div className="flex flex-col gap-2 px-2" role="status" aria-label="Carregando conversas">
            {[0, 1, 2, 3].map((i) => (
              <Skeleton key={i} className="h-8 w-full" />
            ))}
          </div>
        )}
        {conversas?.length === 0 && (
          <p className="px-3 py-2 text-sm text-muted-foreground">Nenhuma conversa ainda. Clique em Nova conversa.</p>
        )}
        {conversas && conversas.length > 0 && grupos.length === 0 && (
          <p className="px-3 py-2 text-sm text-muted-foreground">Nenhuma conversa com “{busca}”.</p>
        )}
        {grupos.map((g) => (
          <section key={g.rotulo} className="mb-3">
            <h2 className="px-3 py-1 text-xs font-medium text-muted-foreground">{g.rotulo}</h2>
            {g.itens.map((c) => (
              <ItemConversa key={c.id} conversa={c} onRenomear={setRenomeando} onApagar={setApagando} />
            ))}
          </section>
        ))}
      </nav>
      <DialogRenomear conversa={renomeando} fechar={() => setRenomeando(null)} recarregar={recarregar} />
      <DialogApagar conversa={apagando} fechar={() => setApagando(null)} recarregar={recarregar} />
    </>
  )
}

function ItemConversa({
  conversa,
  onRenomear,
  onApagar,
}: {
  conversa: Conversa
  onRenomear: (c: Conversa) => void
  onApagar: (c: Conversa) => void
}) {
  return (
    <div className="group/item relative">
      <NavLink
        to={`/c/${conversa.id}`}
        title={conversa.title}
        className={({ isActive }) =>
          cn(
            'block truncate rounded-md py-2 pr-9 pl-3 text-sm hover:bg-sidebar-accent',
            isActive && 'bg-sidebar-accent font-medium',
          )
        }
      >
        {conversa.title}
      </NavLink>
      <DropdownMenu>
        <DropdownMenuTrigger asChild>
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label={`Ações de ${conversa.title}`}
            className="absolute top-1/2 right-1 -translate-y-1/2 opacity-0 group-hover/item:opacity-100 focus-visible:opacity-100 data-[state=open]:opacity-100"
          >
            <MoreHorizontalIcon />
          </Button>
        </DropdownMenuTrigger>
        <DropdownMenuContent align="start">
          <DropdownMenuItem onSelect={() => onRenomear(conversa)}>
            <PencilIcon /> Renomear
          </DropdownMenuItem>
          <ItemCompartilhar conversa={conversa} />
          <DropdownMenuItem variant="destructive" onSelect={() => onApagar(conversa)}>
            <Trash2Icon /> Apagar
          </DropdownMenuItem>
        </DropdownMenuContent>
      </DropdownMenu>
    </div>
  )
}

type PropsDialog = { conversa: Conversa | null; fechar: () => void; recarregar: () => Promise<void> }

function DialogRenomear({ conversa, fechar, recarregar }: PropsDialog) {
  const [titulo, setTitulo] = useState('')
  useEffect(() => setTitulo(conversa?.title ?? ''), [conversa])

  async function salvar(e: FormEvent) {
    e.preventDefault()
    if (!conversa || !titulo.trim()) return
    try {
      await renomearConversa(conversa.id, titulo.trim())
      await recarregar()
      fechar()
    } catch {
      toast.error('Não foi possível renomear a conversa.')
    }
  }

  return (
    <Dialog open={conversa !== null} onOpenChange={(aberto) => !aberto && fechar()}>
      <DialogContent>
        <form onSubmit={salvar} className="flex flex-col gap-4">
          <DialogHeader>
            <DialogTitle>Renomear conversa</DialogTitle>
          </DialogHeader>
          <Input
            aria-label="Novo título"
            value={titulo}
            maxLength={200}
            onChange={(e) => setTitulo(e.target.value)}
            autoFocus
          />
          <DialogFooter>
            <Button type="button" variant="outline" onClick={fechar}>
              Cancelar
            </Button>
            <Button type="submit" disabled={!titulo.trim()}>
              Salvar
            </Button>
          </DialogFooter>
        </form>
      </DialogContent>
    </Dialog>
  )
}

function DialogApagar({ conversa, fechar, recarregar }: PropsDialog) {
  const navigate = useNavigate()
  // useParams no layout pai não vê o :id da rota filha.
  const id = useMatch('/c/:id')?.params.id

  async function apagar() {
    if (!conversa) return
    try {
      await apagarConversa(conversa.id)
      if (id === conversa.id) navigate('/', { replace: true })
      await recarregar()
      toast.success('Conversa apagada.')
    } catch {
      toast.error('Não foi possível apagar a conversa.')
    }
    fechar()
  }

  return (
    <AlertDialog open={conversa !== null} onOpenChange={(aberto) => !aberto && fechar()}>
      <AlertDialogContent>
        <AlertDialogHeader>
          <AlertDialogTitle>Apagar conversa?</AlertDialogTitle>
          <AlertDialogDescription>
            “{conversa?.title}” e todas as mensagens dela serão apagadas. Isso não pode ser desfeito.
          </AlertDialogDescription>
        </AlertDialogHeader>
        <AlertDialogFooter>
          <AlertDialogCancel>Cancelar</AlertDialogCancel>
          <AlertDialogAction variant="destructive" onClick={apagar}>
            Apagar
          </AlertDialogAction>
        </AlertDialogFooter>
      </AlertDialogContent>
    </AlertDialog>
  )
}
