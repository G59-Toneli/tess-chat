import { Link, NavLink, Outlet, useNavigate } from 'react-router'
import { MoonIcon, PlusIcon, SunIcon, UserIcon } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { cn } from '@/lib/utils'
import { conversasMock, usuarioMock } from '@/mock'
import { alternarTema, temaEscuro } from '@/tema'

const itensMenu = [
  { to: '/config', rotulo: 'Configuração' },
  { to: '/tools', rotulo: 'Tools' },
  { to: '/mcp', rotulo: 'Servidores MCP' },
  { to: '/conectores', rotulo: 'Conectores' },
  { to: '/creditos', rotulo: 'Créditos' },
  { to: '/auditoria', rotulo: 'Auditoria' },
]

/** Layout base: sidebar de Conversas, header com menu do Usuário, conteúdo. */
export function AppLayout() {
  const navigate = useNavigate()
  return (
    <div className="flex h-dvh">
      <aside className="flex w-64 shrink-0 flex-col border-r bg-muted/30">
        <div className="p-3">
          <Button className="w-full" variant="outline" asChild>
            <Link to="/">
              <PlusIcon /> Nova conversa
            </Link>
          </Button>
        </div>
        <nav className="flex-1 overflow-y-auto px-2" aria-label="Conversas">
          {conversasMock.map((c) => (
            <NavLink
              key={c.id}
              to={`/c/${c.id}`}
              className={({ isActive }) =>
                cn('block truncate rounded-md px-3 py-2 text-sm hover:bg-muted', isActive && 'bg-muted font-medium')
              }
            >
              {c.titulo}
            </NavLink>
          ))}
        </nav>
      </aside>
      <div className="flex min-w-0 flex-1 flex-col">
        <header className="flex h-14 items-center justify-between border-b px-4">
          <span className="font-semibold">Desafio Chat</span>
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button variant="ghost" size="sm">
                <UserIcon /> {usuarioMock.nome}
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuLabel>{usuarioMock.email}</DropdownMenuLabel>
              <DropdownMenuSeparator />
              {itensMenu.map((i) => (
                <DropdownMenuItem key={i.to} onSelect={() => navigate(i.to)}>
                  {i.rotulo}
                </DropdownMenuItem>
              ))}
              <DropdownMenuSeparator />
              <DropdownMenuItem onSelect={alternarTema}>
                {temaEscuro() ? <SunIcon /> : <MoonIcon />} {temaEscuro() ? 'Tema claro' : 'Tema escuro'}
              </DropdownMenuItem>
              <DropdownMenuItem onSelect={() => navigate('/login')}>Sair</DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </header>
        <main className="min-h-0 flex-1">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
