import { useCallback, useEffect, useState } from 'react'
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from 'recharts'
import { EstadoCarregando, EstadoErro, EstadoVazio } from '@/components/estados'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { ChartContainer, ChartTooltip, ChartTooltipContent, type ChartConfig } from '@/components/ui/chart'
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table'
import { useContextoApp } from '@/layout/AppLayout'
import { fmtDataHora, fmtNumero, painelCredito, usd, usdEixo, type Painel, type Saldo } from '@/lib/painel'
import { cn } from '@/lib/utils'

// Uma série por gráfico: um tom só, sem legenda. A cor vem do tema.
const config = { custo: { label: 'Gasto', color: 'var(--chart-2)' } } satisfies ChartConfig
const fmtDia = new Intl.DateTimeFormat('pt-BR', { day: '2-digit', month: '2-digit' })

/** Dia "AAAA-MM-DD" da API (já no fuso do browser) para Date local. */
const diaLocal = (d: string) => {
  const [a, m, dd] = d.split('-').map(Number)
  return new Date(a, m - 1, dd)
}

type PorModelo = Painel['por_modelo']

/** Top 5 modelos por gasto; o resto vira "Outros" para o eixo não esconder rótulo. */
function top5(linhas: PorModelo): PorModelo {
  if (linhas.length <= 5) return linhas
  const resto = linhas.slice(5)
  const soma = (k: 'custo_micro_usd' | 'chamadas') => resto.reduce((t, l) => t + l[k], 0)
  return [...linhas.slice(0, 5), { model: 'Outros', custo_micro_usd: soma('custo_micro_usd'), chamadas: soma('chamadas') }]
}

/** Saldo, Cap, gasto por dia e por modelo e últimas linhas do Ledger. Admin alterna para o global. */
export function Creditos() {
  const { usuario } = useContextoApp()
  const admin = usuario?.is_superuser ?? false
  const [escopo, setEscopo] = useState<'me' | 'global'>('me')
  const [painel, setPainel] = useState<Painel | null>(null)
  const [erro, setErro] = useState(false)

  const carregar = useCallback(async () => {
    setErro(false)
    setPainel(null)
    try {
      setPainel(await painelCredito(escopo))
    } catch {
      setErro(true)
    }
  }, [escopo])

  useEffect(() => void carregar(), [carregar])

  return (
    <div className="mx-auto max-w-6xl p-8">
      <div className="mb-6 flex items-start justify-between gap-4">
        <div>
          <h1 className="text-2xl font-semibold">Créditos</h1>
          <p className="mt-1 text-sm text-muted-foreground">
            Todo uso de modelo debita do saldo, pelo uso real informado pelo provedor. Saldo = Cap − soma do Ledger.
          </p>
        </div>
        {admin && (
          <div className="flex shrink-0 rounded-lg border p-0.5" role="group" aria-label="Escopo">
            {(['me', 'global'] as const).map((e) => (
              <Button key={e} size="sm" variant={escopo === e ? 'secondary' : 'ghost'} onClick={() => setEscopo(e)}>
                {e === 'me' ? 'Meu crédito' : 'Global'}
              </Button>
            ))}
          </div>
        )}
      </div>

      {erro ? (
        <EstadoErro mensagem="Não foi possível carregar o crédito." onTentarDeNovo={carregar} />
      ) : painel === null ? (
        <EstadoCarregando />
      ) : (
        <div className="flex flex-col gap-6">
          <Resumo saldo={painel.saldo} global={escopo === 'global'} />
          {painel.ultimas.length === 0 ? (
            <EstadoVazio titulo="Nenhum gasto ainda" descricao="Mande uma mensagem no chat e o gasto aparece aqui." />
          ) : (
            <>
              <div className="grid gap-6 lg:grid-cols-2">
                <Card>
                  <CardHeader>
                    <CardTitle>Gasto por dia</CardTitle>
                    <CardDescription>Dias no seu fuso horário.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ChartContainer config={config} className="h-64 w-full">
                      <BarChart data={painel.por_dia} margin={{ left: 8, right: 8 }}>
                        <CartesianGrid vertical={false} />
                        <XAxis dataKey="dia" tickLine={false} axisLine={false} tickFormatter={(d) => fmtDia.format(diaLocal(d))} />
                        <YAxis tickLine={false} axisLine={false} width={80} tickFormatter={(v) => usdEixo(v)} />
                        <ChartTooltip
                          cursor={{ fillOpacity: 0.3 }}
                          content={
                            <ChartTooltipContent
                              labelFormatter={(_, p) => fmtDia.format(diaLocal(p?.[0]?.payload?.dia))}
                              formatter={(v) => usd(Number(v))}
                            />
                          }
                        />
                        <Bar dataKey="custo_micro_usd" name="custo" fill="var(--color-custo)" radius={[4, 4, 0, 0]} maxBarSize={48} />
                      </BarChart>
                    </ChartContainer>
                  </CardContent>
                </Card>
                <Card>
                  <CardHeader>
                    <CardTitle>Gasto por modelo</CardTitle>
                    <CardDescription>Soma do Ledger por modelo, com o número de chamadas.</CardDescription>
                  </CardHeader>
                  <CardContent>
                    <ChartContainer config={config} className="h-64 w-full">
                      <BarChart data={top5(painel.por_modelo)} layout="vertical" margin={{ left: 8, right: 32 }}>
                        <CartesianGrid horizontal={false} />
                        <XAxis type="number" tickLine={false} axisLine={false} tickFormatter={(v) => usdEixo(v)} />
                        <YAxis type="category" dataKey="model" tickLine={false} axisLine={false} width={150} interval={0} />
                        <ChartTooltip
                          cursor={{ fillOpacity: 0.3 }}
                          content={
                            <ChartTooltipContent
                              formatter={(v, _n, item) =>
                                `${usd(Number(v))} · ${fmtNumero.format(item.payload.chamadas)} chamadas`
                              }
                            />
                          }
                        />
                        <Bar dataKey="custo_micro_usd" name="custo" fill="var(--color-custo)" radius={[0, 4, 4, 0]} maxBarSize={32} />
                      </BarChart>
                    </ChartContainer>
                  </CardContent>
                </Card>
              </div>
              <Card>
                <CardHeader>
                  <CardTitle>Últimas linhas do Ledger</CardTitle>
                  <CardDescription>Um débito por chamada ao modelo. Somente-inserção.</CardDescription>
                </CardHeader>
                <CardContent>
                  <Table>
                    <TableHeader>
                      <TableRow>
                        <TableHead>Data e hora</TableHead>
                        <TableHead>Modelo</TableHead>
                        <TableHead className="text-right">Entrada</TableHead>
                        <TableHead className="text-right">Saída</TableHead>
                        <TableHead className="text-right">Raciocínio</TableHead>
                        <TableHead className="text-right">Cache</TableHead>
                        <TableHead className="text-right">Custo</TableHead>
                      </TableRow>
                    </TableHeader>
                    <TableBody>
                      {painel.ultimas.map((l) => (
                        <TableRow key={l.id}>
                          <TableCell className="whitespace-nowrap tabular-nums">{fmtDataHora.format(new Date(l.ts))}</TableCell>
                          <TableCell>{l.model}</TableCell>
                          <TableCell className="text-right tabular-nums">{fmtNumero.format(l.input_tokens)}</TableCell>
                          <TableCell className="text-right tabular-nums">{fmtNumero.format(l.output_tokens)}</TableCell>
                          <TableCell className="text-right tabular-nums">{fmtNumero.format(l.thinking_tokens)}</TableCell>
                          <TableCell className="text-right tabular-nums">{fmtNumero.format(l.cache_read_tokens)}</TableCell>
                          <TableCell className="text-right tabular-nums">{usd(l.cost_micro_usd)}</TableCell>
                        </TableRow>
                      ))}
                    </TableBody>
                  </Table>
                </CardContent>
              </Card>
            </>
          )}
        </div>
      )}
    </div>
  )
}

/** Três números e a barra de uso do Cap. Reusado no /admin. */
export function Resumo({ saldo, global }: { saldo: Saldo; global: boolean }) {
  const uso = saldo.cap_micro_usd > 0 ? Math.min(1, saldo.gasto_micro_usd / saldo.cap_micro_usd) : 1
  const alto = uso >= 0.9
  return (
    <Card>
      <CardContent className="flex flex-col gap-4">
        <div className="grid grid-cols-3 gap-6">
          <Numero rotulo="Saldo" valor={usd(saldo.saldo_micro_usd)} destaque />
          <Numero rotulo="Gasto" valor={usd(saldo.gasto_micro_usd)} />
          <Numero rotulo={global ? 'Cap global' : 'Cap'} valor={usd(saldo.cap_micro_usd)} />
        </div>
        <div>
          <div
            className="h-2 overflow-hidden rounded-full bg-muted"
            role="progressbar"
            aria-label="Uso do Cap"
            aria-valuemin={0}
            aria-valuemax={100}
            aria-valuenow={Math.round(uso * 100)}
          >
            <div className={cn('h-full rounded-full', alto ? 'bg-destructive' : 'bg-primary')} style={{ width: `${uso * 100}%` }} />
          </div>
          <p className={cn('mt-1.5 text-xs', alto ? 'text-destructive' : 'text-muted-foreground')}>
            {(uso * 100).toLocaleString('pt-BR', { maximumFractionDigits: 2 })}% do Cap usado
            {alto && ' · perto do limite: novas chamadas serão recusadas ao atingir o Cap'}
          </p>
        </div>
      </CardContent>
    </Card>
  )
}

function Numero({ rotulo, valor, destaque }: { rotulo: string; valor: string; destaque?: boolean }) {
  return (
    <div>
      <p className="text-sm text-muted-foreground">{rotulo}</p>
      <p className={cn('tabular-nums', destaque ? 'text-3xl font-semibold' : 'text-2xl')}>{valor}</p>
    </div>
  )
}
