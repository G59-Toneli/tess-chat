import { useCallback, useEffect, useMemo, useState, type FormEvent, type ReactNode } from 'react'
import { useSearchParams } from 'react-router'
import { toast } from 'sonner'
import { EstadoCarregando, EstadoErro } from '@/components/estados'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Select, SelectContent, SelectItem, SelectTrigger, SelectValue } from '@/components/ui/select'
import { Switch } from '@/components/ui/switch'
import { useContextoApp } from '@/layout/AppLayout'
import { ErroApi } from '@/lib/api'
import {
  MODELOS,
  NIVEIS,
  lerConfig,
  salvarConfig,
  type Configuracao as Efetiva,
  type RespostaConfig,
  type Valores,
} from '@/lib/configuracao'
import { fmtNumero } from '@/lib/painel'
import { alternarTema, temaEscuro } from '@/tema'

const HERDAR = '__herdar__'
const CONTA = '__conta__'

// Estado do formulário em texto. Vazio (ou HERDAR nos selects) = herda do escopo de cima.
type Form = Record<keyof Efetiva, string>

function paraForm(v: Valores): Form {
  return {
    modelo: v.modelo ?? HERDAR,
    nivel_raciocinio: v.nivel_raciocinio ?? HERDAR,
    compactacao_limiar: v.compactacao_limiar?.toString() ?? '',
    roteador_limiar: v.roteador_limiar?.toString().replace('.', ',') ?? '',
    tool_calls_limite: v.tool_calls_limite?.toString() ?? '',
  }
}

function paraValores(f: Form): Valores {
  const num = (s: string) => (s.trim() === '' ? null : Number(s.replace(',', '.')))
  return {
    modelo: f.modelo === HERDAR ? null : f.modelo,
    nivel_raciocinio: f.nivel_raciocinio === HERDAR ? null : f.nivel_raciocinio,
    compactacao_limiar: num(f.compactacao_limiar),
    roteador_limiar: num(f.roteador_limiar),
    tool_calls_limite: num(f.tool_calls_limite),
  }
}

const rotulo = (lista: { valor: string; rotulo: string }[], v: string) => lista.find((i) => i.valor === v)?.rotulo ?? v
const decimal = (n: number) => n.toLocaleString('pt-BR')

/** /config: modelo, nível de raciocínio, limiares e tema. Escopo: a conta ou uma Conversa. */
export function Configuracao() {
  const { conversas } = useContextoApp()
  const [params, setParams] = useSearchParams()
  const conversa = params.get('conversa')
  const [dados, setDados] = useState<RespostaConfig | null>(null)
  const [form, setForm] = useState<Form | null>(null)
  const [erro, setErro] = useState(false)
  const [salvando, setSalvando] = useState(false)

  const carregar = useCallback(async () => {
    setErro(false)
    setDados(null)
    try {
      const r = await lerConfig(conversa)
      setDados(r)
      setForm(paraForm(r.valores))
    } catch {
      setErro(true)
    }
  }, [conversa])

  useEffect(() => void carregar(), [carregar])

  // Só os campos que mudaram vão no PUT: o evento settings_changed fica com o diff real.
  const mudancas = useMemo(() => {
    if (!dados || !form) return {}
    const novos = paraValores(form)
    const chaves = (Object.keys(novos) as (keyof Valores)[]).filter((k) => novos[k] !== dados.valores[k])
    return Object.fromEntries(chaves.map((k) => [k, novos[k]])) as Partial<Valores>
  }, [dados, form])
  const sujo = Object.keys(mudancas).length > 0

  async function salvar(e: FormEvent) {
    e.preventDefault()
    setSalvando(true)
    try {
      const r = await salvarConfig(conversa, mudancas)
      setDados(r)
      setForm(paraForm(r.valores))
      toast.success('Configuração salva. Vale a partir da próxima mensagem.')
    } catch (err) {
      toast.error(
        err instanceof ErroApi && err.status === 422
          ? 'Confira os valores: algum está fora do limite.'
          : 'Não foi possível salvar. Tente de novo.',
      )
    } finally {
      setSalvando(false)
    }
  }

  const escopo = conversa ? 'desta conversa' : 'da sua conta'
  const origem = conversa ? 'da conta' : 'padrão'

  return (
    <div className="mx-auto h-full max-w-3xl space-y-6 overflow-y-auto px-4 py-8">
      <div className="space-y-1">
        <h1 className="text-2xl font-semibold">Configuração</h1>
        <p className="text-sm text-muted-foreground">
          A conversa sobrepõe a conta, e a conta sobrepõe o padrão. Campo vazio herda o valor de cima.
        </p>
      </div>

      <div className="flex flex-col gap-2">
        <Label htmlFor="escopo">Aplicar em</Label>
        <Select value={conversa ?? CONTA} onValueChange={(v) => setParams(v === CONTA ? {} : { conversa: v })}>
          <SelectTrigger id="escopo" className="w-full sm:w-96">
            <SelectValue />
          </SelectTrigger>
          <SelectContent>
            <SelectItem value={CONTA}>Minha conta (todas as conversas)</SelectItem>
            {(conversas ?? []).map((c) => (
              <SelectItem key={c.id} value={c.id}>
                Conversa: {c.title}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>

      {erro ? (
        <EstadoErro mensagem="Não foi possível carregar a configuração." onTentarDeNovo={carregar} />
      ) : !dados || !form ? (
        <EstadoCarregando />
      ) : (
        <form onSubmit={salvar} className="space-y-6">
          <Card>
            <CardHeader>
              <CardTitle>Modelo</CardTitle>
              <CardDescription>
                Modelo e raciocínio {escopo}. Mais raciocínio deixa a resposta mais lenta e mais cara.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-5 md:grid-cols-2">
              <Campo
                id="modelo"
                rotulo="Modelo"
                efetivo={rotulo(MODELOS, dados.efetiva.modelo)}
                proprio={dados.valores.modelo !== null}
              >
                <Select value={form.modelo} onValueChange={(v) => setForm({ ...form, modelo: v })}>
                  <SelectTrigger id="modelo" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={HERDAR}>
                      Herdar {origem}: {rotulo(MODELOS, dados.herdada.modelo)}
                    </SelectItem>
                    {MODELOS.map((m) => (
                      <SelectItem key={m.valor} value={m.valor}>
                        {m.rotulo}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Campo>
              <Campo
                id="nivel"
                rotulo="Nível de raciocínio"
                efetivo={rotulo(NIVEIS, dados.efetiva.nivel_raciocinio)}
                proprio={dados.valores.nivel_raciocinio !== null}
              >
                <Select value={form.nivel_raciocinio} onValueChange={(v) => setForm({ ...form, nivel_raciocinio: v })}>
                  <SelectTrigger id="nivel" className="w-full">
                    <SelectValue />
                  </SelectTrigger>
                  <SelectContent>
                    <SelectItem value={HERDAR}>
                      Herdar {origem}: {rotulo(NIVEIS, dados.herdada.nivel_raciocinio)}
                    </SelectItem>
                    {NIVEIS.map((n) => (
                      <SelectItem key={n.valor} value={n.valor}>
                        {n.rotulo}
                      </SelectItem>
                    ))}
                  </SelectContent>
                </Select>
              </Campo>
            </CardContent>
          </Card>

          <Card>
            <CardHeader>
              <CardTitle>Limiares</CardTitle>
              <CardDescription>
                Quando a compactação dispara, quando o Roteador força uma tool e quantas tools cabem num turno.
              </CardDescription>
            </CardHeader>
            <CardContent className="grid gap-5 md:grid-cols-2">
              <Campo
                id="compactacao"
                rotulo="Limiar de compactação (tokens)"
                efetivo={fmtNumero.format(dados.efetiva.compactacao_limiar)}
                proprio={dados.valores.compactacao_limiar !== null}
                ajuda="Se a entrada do turno anterior passar disso, as mensagens antigas viram um resumo. De 1 a 1.000.000."
              >
                <Input
                  id="compactacao"
                  inputMode="numeric"
                  placeholder={`Herdar ${origem}: ${fmtNumero.format(dados.herdada.compactacao_limiar)}`}
                  value={form.compactacao_limiar}
                  onChange={(e) => setForm({ ...form, compactacao_limiar: e.target.value.replace(/\D/g, '') })}
                />
              </Campo>
              <Campo
                id="roteador"
                rotulo="Limiar do Roteador"
                efetivo={decimal(dados.efetiva.roteador_limiar)}
                proprio={dados.valores.roteador_limiar !== null}
                ajuda="Confiança mínima do Roteador para forçar a tool. De 0 a 1. Abaixo disso o modelo decide."
              >
                <Input
                  id="roteador"
                  inputMode="decimal"
                  placeholder={`Herdar ${origem}: ${decimal(dados.herdada.roteador_limiar)}`}
                  value={form.roteador_limiar}
                  onChange={(e) => setForm({ ...form, roteador_limiar: e.target.value.replace(/[^\d.,]/g, '') })}
                />
              </Campo>
              <Campo
                id="tool-calls"
                rotulo="Chamadas de tool por turno"
                efetivo={fmtNumero.format(dados.efetiva.tool_calls_limite)}
                proprio={dados.valores.tool_calls_limite !== null}
                ajuda="Quantas chamadas de tool um turno pode fazer. MCPs genéricos gastam 3 por ação. De 1 a 50."
              >
                <Input
                  id="tool-calls"
                  inputMode="numeric"
                  placeholder={`Herdar ${origem}: ${fmtNumero.format(dados.herdada.tool_calls_limite)}`}
                  value={form.tool_calls_limite}
                  onChange={(e) => setForm({ ...form, tool_calls_limite: e.target.value.replace(/\D/g, '') })}
                />
              </Campo>
            </CardContent>
          </Card>

          <div className="flex flex-col-reverse gap-2 md:flex-row md:items-center md:justify-end">
            <Button
              type="button"
              variant="outline"
              disabled={!sujo || salvando}
              onClick={() => setForm(paraForm(dados.valores))}
            >
              Descartar
            </Button>
            <Button type="submit" disabled={!sujo || salvando}>
              {salvando ? 'Salvando...' : 'Salvar'}
            </Button>
          </div>
        </form>
      )}

      <Card>
        <CardHeader className="flex flex-row items-center justify-between gap-4">
          <div className="space-y-1.5">
            <CardTitle>Tema</CardTitle>
            <CardDescription>Vale só neste navegador.</CardDescription>
          </div>
          <TemaEscuro />
        </CardHeader>
      </Card>
    </div>
  )
}

function Campo({
  id,
  rotulo,
  efetivo,
  proprio,
  ajuda,
  children,
}: {
  id: string
  rotulo: string
  efetivo: string
  proprio: boolean
  ajuda?: string
  children: ReactNode
}) {
  return (
    <div className="flex min-w-0 flex-col gap-2">
      <Label htmlFor={id}>{rotulo}</Label>
      {children}
      <p className="flex flex-wrap items-center gap-1.5 text-xs text-muted-foreground">
        Em uso: <span className="font-medium text-foreground">{efetivo}</span>
        <Badge variant="outline">{proprio ? 'próprio' : 'herdado'}</Badge>
      </p>
      {ajuda && <p className="text-xs text-muted-foreground">{ajuda}</p>}
    </div>
  )
}

function TemaEscuro() {
  const [escuro, setEscuro] = useState(temaEscuro)
  return (
    <div className="flex items-center gap-2">
      <Label htmlFor="tema" className="text-sm text-muted-foreground">
        Escuro
      </Label>
      <Switch
        id="tema"
        checked={escuro}
        onCheckedChange={() => {
          alternarTema()
          setEscuro(temaEscuro())
        }}
      />
    </div>
  )
}
