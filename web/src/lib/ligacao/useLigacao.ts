// Estado de uma Ligação: microfone, WebSocket, fila de áudio e tela. Montar liga; desmontar encerra tudo.
import { useCallback, useEffect, useRef, useState } from 'react'
import { abrirMicrofone, type Microfone } from './captura'
import { LIMITE_PADRAO_S } from './config'
import {
  ErroLigacao,
  TEXTO_MICROFONE,
  TEXTO_QUEDA,
  capNoFechamento,
  pedirTicket,
  textoFechamento,
  textoFim,
  urlWs,
  type MensagemBrowser,
  type MensagemServidor,
  type MotivoFim,
  type Origem,
} from './protocolo'
import { FilaAudio } from './reproducao'
import { compartilharTela, suportaTela, type Tela } from './tela'

export type EstadoLigacao = 'conectando' | 'em_ligacao' | 'encerrando' | 'encerrada' | 'erro'
export type Fala = { id: number; origem: Origem; texto: string; final: boolean }

// Recursos de uma montagem. Cada execução do efeito tem o seu: o StrictMode monta duas vezes.
type Recursos = {
  ws: WebSocket | null
  mic: Microfone | null
  fila: FilaAudio | null
  tela: Tela | null
  pronto: boolean
  motivo: MotivoFim | null
  erro: string | null
  desligou: boolean
}

let ultimoId = 0

/** O servidor manda o texto acumulado da fala (api/app/voz.py): troca o da fala aberta. `final` fecha. */
function juntarFala(falas: Fala[], origem: Origem, texto: string, final: boolean): Fala[] {
  const i = falas.findLastIndex((f) => f.origem === origem && !f.final)
  if (i < 0) return [...falas, { id: ++ultimoId, origem, texto, final }]
  return falas.with(i, { ...falas[i], texto, final })
}

function enviar(x: Recursos, m: MensagemBrowser) {
  if (x.ws?.readyState === WebSocket.OPEN) x.ws.send(JSON.stringify(m))
}

function liberar(x: Recursos) {
  x.mic?.parar()
  x.tela?.parar()
  x.fila?.fechar()
  x.mic = x.tela = x.fila = null
}

export function useLigacao(conversaId: string) {
  const [estado, setEstado] = useState<EstadoLigacao>('conectando')
  const [aviso, setAviso] = useState<string | null>(null)
  const [cap, setCap] = useState(false)
  const [limiteS, setLimiteS] = useState(LIMITE_PADRAO_S)
  const [inicio, setInicio] = useState<number | null>(null)
  const [falas, setFalas] = useState<Fala[]>([])
  const [mudo, setMudo] = useState(false)
  const [fila, setFila] = useState(0)
  const [tela, setTela] = useState<MediaStream | null>(null)
  const [desligouAqui, setDesligouAqui] = useState(false)
  const atual = useRef<Recursos | null>(null)

  useEffect(() => {
    const x: Recursos = { ws: null, mic: null, fila: null, tela: null, pronto: false, motivo: null, erro: null, desligou: false }
    atual.current = x
    let vivo = true
    const falhar = (texto: string, ehCap = false) => {
      liberar(x)
      if (!vivo) return
      setTela(null)
      setAviso(texto)
      setCap(ehCap)
      setEstado('erro')
    }

    async function abrir() {
      // Microfone antes do ticket: a permissão pode levar segundos, e o ticket vale 30 s e uma vez só.
      let mic: Microfone
      try {
        mic = await abrirMicrofone((pcm) => {
          if (x.pronto && x.ws?.readyState === WebSocket.OPEN) x.ws.send(pcm)
        })
      } catch {
        return falhar(TEXTO_MICROFONE)
      }
      if (!vivo) return mic.parar()
      x.mic = mic
      x.fila = new FilaAudio(setFila)

      let ticket: string
      try {
        ticket = await pedirTicket(conversaId)
      } catch (e) {
        return e instanceof ErroLigacao ? falhar(e.message, e.cap) : falhar(TEXTO_QUEDA)
      }
      if (!vivo) return

      const ws = new WebSocket(urlWs(ticket))
      ws.binaryType = 'arraybuffer'
      x.ws = ws
      ws.onmessage = (ev: MessageEvent<ArrayBuffer | string>) => {
        if (typeof ev.data !== 'string') return x.fila?.tocar(ev.data)
        let m: MensagemServidor
        try {
          m = JSON.parse(ev.data)
        } catch {
          return
        }
        if (m.tipo === 'pronto') {
          x.pronto = true
          setLimiteS(m.limite_s ?? LIMITE_PADRAO_S)
          setInicio(Date.now())
          setEstado('em_ligacao')
        } else if (m.tipo === 'transcricao') {
          setFalas((f) => juntarFala(f, m.origem, m.texto, m.final))
        } else if (m.tipo === 'interrompido') {
          // A fala cortada do agente segue aberta: o servidor fecha no turn_complete.
          x.fila?.esvaziar()
        } else if (m.tipo === 'fim') {
          x.motivo = m.motivo
        } else if (m.tipo === 'erro') {
          x.erro = m.mensagem
          setAviso(m.mensagem)
        }
      }
      ws.onclose = (ev) => {
        x.ws = null
        x.pronto = false
        const recusa = textoFechamento(ev.code)
        if (recusa) return falhar(recusa, capNoFechamento(ev.code))
        if (x.motivo === 'erro' || x.motivo === 'queda') return falhar(x.erro ?? textoFim(x.motivo))
        if (!x.motivo && !x.desligou) return falhar(x.erro ?? TEXTO_QUEDA)
        liberar(x)
        if (!vivo) return
        setTela(null)
        setAviso(textoFim(x.motivo ?? 'desligou'))
        setEstado('encerrada')
      }
    }

    void abrir()
    // Fechar a aba: avisa o servidor antes de o browser derrubar a conexão.
    const aoSairDaPagina = () => enviar(x, { tipo: 'desligar' })
    window.addEventListener('pagehide', aoSairDaPagina)
    return () => {
      vivo = false
      window.removeEventListener('pagehide', aoSairDaPagina)
      enviar(x, { tipo: 'desligar' })
      x.ws?.close()
      liberar(x)
    }
  }, [conversaId])

  const alternarMudo = useCallback(() => {
    setMudo((m) => {
      atual.current?.mic?.mutar(!m)
      return !m
    })
  }, [])

  const alternarTela = useCallback(async () => {
    const x = atual.current
    if (!x) return
    if (x.tela) {
      x.tela.parar()
      x.tela = null
      setTela(null)
      return enviar(x, { tipo: 'tela', ativa: false })
    }
    let t: Tela
    try {
      t = await compartilharTela(
        (jpeg) => enviar(x, { tipo: 'frame', jpeg }),
        // Parou pela barra do browser.
        () => {
          x.tela = null
          setTela(null)
          enviar(x, { tipo: 'tela', ativa: false })
        },
      )
    } catch {
      return // O usuário fechou a escolha de tela.
    }
    if (atual.current !== x || !x.pronto) return t.parar()
    x.tela = t
    setTela(t.stream)
    enviar(x, { tipo: 'tela', ativa: true })
  }, [])

  const desligar = useCallback(() => {
    const x = atual.current
    if (!x?.ws) return
    x.desligou = true
    setDesligouAqui(true)
    setEstado('encerrando')
    enviar(x, { tipo: 'desligar' })
    x.mic?.parar()
    x.tela?.parar()
    x.mic = x.tela = null
    setTela(null)
    // O servidor fecha depois do `fim`. Se não fechar, fecha daqui.
    const ws = x.ws
    setTimeout(() => ws.close(), 3000)
  }, [])

  return {
    estado,
    aviso,
    cap,
    limiteS,
    inicio,
    falas,
    mudo,
    /** Chunks de áudio do agente ainda na fila. */
    fila,
    tela,
    telaSuportada: suportaTela(),
    desligouAqui,
    alternarMudo,
    alternarTela,
    desligar,
  }
}

export type Ligacao = ReturnType<typeof useLigacao>
