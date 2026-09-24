import { useCallback, useEffect, useMemo, useState } from 'react'
import { useSearchParams } from 'react-router'
import { ChevronLeftIcon, ChevronRightIcon, XIcon } from 'lucide-react'
import { EstadoCarregando, EstadoErro, EstadoVazio } from '@/components/estados'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from '@/components/ui/sheet'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useContextoApp } from '@/layout/AppLayout'
import {
  fmtDataHora,
  fmtNumero,
  listarEventos,
  rotuloEvento,
  tiposDeEvento,
  usd,
  usuariosAdmin,
  type Evento,
  type PaginaEventos,
  type UsuarioAdmin,
} from '@/lib/painel'

const POR_PAGINA = 25
const TODOS = '__todos'

/** Início ou fim do dia local (input date) em ISO, para o filtro de período. */
function limiteDoDia(dia: string, fim: boolean): string | undefined {
  if (!dia) return undefined
  const [a, m, d] = dia.split('-').map(Number)
  return (fim ? new Date(a, m - 1, d, 23, 59, 59, 999) : new Date(a, m - 1, d)).toISOString()
}

/** Tabela de Eventos de auditoria com filtros na URL, paginação e detalhe em drawer. */
export function Auditoria() {
  const { usuario, conversas } = useContextoApp()
  const admin = usuario?.is_superuser ?? false
  const [params, setParams] = useSearchParams()
  const filtro = {
    usuario: params.get('usuario') ?? '',
    conversa: params.get('conversa') ?? '',
    tipo: params.get('tipo') ?? '',
    de: params.get('de') ?? '',
    ate: params.get('ate') ?? '',
    pagina: Number(params.get('pagina') ?? '0'),
  }
  const [pagina, setPagina] = useState<PaginaEventos | null>(null)
  const [erro, setErro] = useState(false)
  const [tipos, setTipos] = useState<string[]>([])
  const [usuarios, setUsuarios] = useState<UsuarioAdmin[]>([])
  const [aberto, setAberto] = useState<Evento | null>(null)

  const titulos = useMemo(() => new Map((conversas ?? []).map((c) => [c.id, c.title])), [conversas])
  const chave = params.toString()

  const carregar = useCallback(async () => {
    setErro(false)
    setPagina(null)
    const p = new URLSearchParams(chave)
    try {
      setPagina(
        await listarEventos({
          user_id: p.get('usuario') ?? undefined,
          conversation_id: p.get('conversa') ?? undefined,
          event_type: p.get('tipo') ?? undefined,
          desde: limiteDoDia(p.get('de') ?? '', false),
          ate: limiteDoDia(p.get('ate') ?? '', true),
          limit: POR_PAGINA,
          offset: Number(p.get('pagina') ?? '0') * POR_PAGINA,
        }),
      )
    } catch {
      setErro(true)
    }
  }, [chave])

  useEffect(() => void carregar(), [carregar])
  useEffect(() => {
    tiposDeEvento().then(setTipos, () => undefined)
  }, [])
  useEffect(() => {
    if (admin) usuariosAdmin().then(setUsuarios, () => undefined)
  }, [admin])

  function mudar(campo: string, valor: string) {
    const novo = new URLSearchParams(params)
    if (valor && valor !== TODOS) novo.set(campo, valor)
    else novo.delete(campo)
    if (campo !== 'pagina') novo.delete('pagina')
    setParams(novo)
  }

  const temFiltro = ['usuario', 'conversa', 'tipo', 'de', 'ate'].some((k) => params.get(k))
  const inicio = filtro.pagina * POR_PAGINA

  return (
    <div className="mx-auto max-w-6xl p-4 md:p-8">
      <h1 className="text-2xl font-semibold">Auditoria</h1>
      <p className="mt-1 mb-6 text-sm text-muted-foreground">
        {admin
          ? 'Todos os eventos do app, do mais recente para o mais antigo. Clique numa linha para ver o payload.'
          : 'Seus eventos, do mais recente para o mais antigo. Clique numa linha para ver o payload.'}
      </p>

      <div className="mb-4 flex flex-col gap-3 md:flex-row md:flex-wrap md:items-end">
        {admin && (
          <Filtro rotulo="Usuário" id="f-usuario">
            <Select value={filtro.usuario || TODOS} onValueChange={(v) => mudar('usuario', v)}>
              <SelectTrigger id="f-usuario" className="w-full md:w-44">
                <SelectValue />
              </SelectTrigger>
              <SelectContent>
                <SelectItem value={TODOS}>Todos</SelectItem>
                {usuarios.map((u) => (
                  <SelectItem key={u.id} value={u.id}>
                    {u.email}
                  </SelectItem>
                ))}
              </SelectContent>
            </Select>
          </Filtro>
        )}
        <Filtro rotulo="Conversa" id="f-conversa">
          <Select value={filtro.conversa || TODOS} onValueChange={(v) => mudar('conversa', v)}>
            <SelectTrigger id="f-conversa" className="w-full md:w-44">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={TODOS}>Todas</SelectItem>
              {filtro.conversa && !titulos.has(filtro.conversa) && (
                <SelectItem value={filtro.conversa}>{filtro.conversa.slice(0, 8)}…</SelectItem>
              )}
              {(conversas ?? []).map((c) => (
                <SelectItem key={c.id} value={c.id}>
                  <span className="max-w-44 truncate">{c.title}</span>
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Filtro>
        <Filtro rotulo="Tipo" id="f-tipo">
          <Select value={filtro.tipo || TODOS} onValueChange={(v) => mudar('tipo', v)}>
            <SelectTrigger id="f-tipo" className="w-full md:w-40">
              <SelectValue />
            </SelectTrigger>
            <SelectContent>
              <SelectItem value={TODOS}>Todos</SelectItem>
              {tipos.map((t) => (
                <SelectItem key={t} value={t}>
                  {rotuloEvento(t)}
                </SelectItem>
              ))}
            </SelectContent>
          </Select>
        </Filtro>
        <Filtro rotulo="De" id="f-de">
          <Input id="f-de" type="date" className="w-full md:w-36" value={filtro.de} onChange={(e) => mudar('de', e.target.value)} />
        </Filtro>
        <Filtro rotulo="Até" id="f-ate">
          <Input id="f-ate" type="date" className="w-full md:w-36" value={filtro.ate} onChange={(e) => mudar('ate', e.target.value)} />
        </Filtro>
        {temFiltro && (
          <Button variant="ghost" onClick={() => setParams({})}>
            <XIcon /> Limpar filtros
          </Button>
        )}
      </div>

      {erro ? (
        <EstadoErro mensagem="Não foi possível carregar os eventos." onTentarDeNovo={carregar} />
      ) : pagina === null ? (
        <EstadoCarregando />
      ) : pagina.items.length === 0 ? (
        <EstadoVazio
          titulo={temFiltro ? 'Nenhum evento com esses filtros' : 'Nenhum evento ainda'}
          descricao={temFiltro ? 'Mude ou limpe os filtros.' : 'Login, mensagens, tools e links aparecem aqui.'}
          acao={
            temFiltro && (
              <Button variant="outline" onClick={() => setParams({})}>
                Limpar filtros
              </Button>
            )
          }
        />
      ) : (
        <>
          <div className="rounded-lg border">
            <Table>
              <TableHeader>
                <TableRow>
                  <TableHead>Data e hora</TableHead>
                  <TableHead>Tipo</TableHead>
                  {admin && <TableHead className="hidden md:table-cell">Usuário</TableHead>}
                  <TableHead>Conversa</TableHead>
                  <TableHead className="hidden md:table-cell">Modelo</TableHead>
                  <TableHead className="hidden text-right md:table-cell">Tokens (entrada / saída)</TableHead>
                  <TableHead className="text-right">Custo</TableHead>
                  <TableHead className="hidden text-right md:table-cell">Latência</TableHead>
                </TableRow>
              </TableHeader>
              <TableBody>
                {pagina.items.map((e) => (
                  <TableRow
                    key={e.id}
                    tabIndex={0}
                    className="cursor-pointer"
                    onClick={() => setAberto(e)}
                    onKeyDown={(k) => (k.key === 'Enter' || k.key === ' ') && setAberto(e)}
                  >
                    <TableCell className="whitespace-nowrap tabular-nums">{fmtDataHora.format(new Date(e.ts))}</TableCell>
                    <TableCell>
                      <Badge variant={e.event_type === 'cap_reached' || e.event_type.includes('error') || e.event_type === 'login_failed' ? 'destructive' : 'secondary'}>
                        {rotuloEvento(e.event_type)}
                      </Badge>
                    </TableCell>
                    {admin && <TableCell className="hidden max-w-48 truncate md:table-cell">{e.user_email ?? '—'}</TableCell>}
                    <TableCell className="max-w-48 truncate">
                      {e.conversation_id ? (titulos.get(e.conversation_id) ?? `${e.conversation_id.slice(0, 8)}…`) : '—'}
                    </TableCell>
                    <TableCell className="hidden text-muted-foreground md:table-cell">{e.model ?? '—'}</TableCell>
                    <TableCell className="hidden text-right tabular-nums md:table-cell">
                      {e.input_tokens != null ? `${fmtNumero.format(e.input_tokens)} / ${fmtNumero.format(e.output_tokens ?? 0)}` : '—'}
                    </TableCell>
                    <TableCell className="text-right tabular-nums">{e.cost_micro_usd != null ? usd(e.cost_micro_usd) : '—'}</TableCell>
                    <TableCell className="hidden text-right tabular-nums md:table-cell">{e.latency_ms != null ? `${fmtNumero.format(e.latency_ms)} ms` : '—'}</TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </div>
          <div className="mt-3 flex flex-wrap items-center justify-between gap-2 text-sm text-muted-foreground">
            <span>
              {inicio + 1}–{inicio + pagina.items.length} de {fmtNumero.format(pagina.total)} eventos
            </span>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" className="h-10 md:h-8" disabled={filtro.pagina === 0} onClick={() => mudar('pagina', String(filtro.pagina - 1))}>
                <ChevronLeftIcon /> Anterior
              </Button>
              <Button
                variant="outline"
                size="sm"
                className="h-10 md:h-8"
                disabled={inicio + pagina.items.length >= pagina.total}
                onClick={() => mudar('pagina', String(filtro.pagina + 1))}
              >
                Próxima <ChevronRightIcon />
              </Button>
            </div>
          </div>
        </>
      )}

      <Sheet open={aberto !== null} onOpenChange={(a) => !a && setAberto(null)}>
        <SheetContent className="overflow-y-auto data-[side=right]:w-full sm:max-w-xl">
          {aberto && <DetalheEvento evento={aberto} tituloConversa={titulos.get(aberto.conversation_id ?? '')} />}
        </SheetContent>
      </Sheet>
    </div>
  )
}

function Filtro({ rotulo, id, children }: { rotulo: string; id: string; children: React.ReactNode }) {
  return (
    <div className="flex flex-col gap-1.5">
      <Label htmlFor={id} className="text-xs text-muted-foreground">
        {rotulo}
      </Label>
      {children}
    </div>
  )
}

function DetalheEvento({ evento: e, tituloConversa }: { evento: Evento; tituloConversa?: string }) {
  const campos: [string, string][] = [
    ['Data e hora', fmtDataHora.format(new Date(e.ts))],
    ['Usuário', e.user_email ?? e.user_id ?? '—'],
    ['Conversa', e.conversation_id ? `${tituloConversa ?? ''} ${e.conversation_id}`.trim() : '—'],
    ['Modelo', e.model ?? '—'],
    ['Tokens de entrada', e.input_tokens != null ? fmtNumero.format(e.input_tokens) : '—'],
    ['Tokens de saída', e.output_tokens != null ? fmtNumero.format(e.output_tokens) : '—'],
    ['Custo', e.cost_micro_usd != null ? `${usd(e.cost_micro_usd)} (${fmtNumero.format(e.cost_micro_usd)} µUSD)` : '—'],
    ['Latência', e.latency_ms != null ? `${fmtNumero.format(e.latency_ms)} ms` : '—'],
  ]
  return (
    <>
      <SheetHeader>
        <SheetTitle>{rotuloEvento(e.event_type)}</SheetTitle>
        <SheetDescription>
          Evento #{e.id} · <code className="text-xs">{e.event_type}</code>
        </SheetDescription>
      </SheetHeader>
      <div className="flex flex-col gap-6 px-4 pb-6">
        <dl className="grid grid-cols-[auto_1fr] gap-x-4 gap-y-2 text-sm">
          {campos.map(([k, v]) => (
            <div key={k} className="contents">
              <dt className="text-muted-foreground">{k}</dt>
              <dd className="min-w-0 break-all">{v}</dd>
            </div>
          ))}
        </dl>
        <div>
          <h3 className="mb-2 text-sm font-medium">Payload</h3>
          <pre className="overflow-x-auto rounded-md border bg-muted/40 p-3 text-xs leading-relaxed">
            {JSON.stringify(e.payload, null, 2)}
          </pre>
        </div>
      </div>
    </>
  )
}
