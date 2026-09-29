// Smoke real da Ligação (ticket 80): Gemini Live de verdade, sem microfone e sem monitor.
// Fala: --use-file-for-fake-audio-capture com um WAV pt-BR (SAPI, 16 kHz mono) precedido de 8 s de
// silêncio, para dar tempo de compartilhar a tela antes da pergunta. Tela: um canvas com texto conhecido no
// lugar do getDisplayMedia (com --use-fake-device-for-media-stream, necessário para a fala de arquivo, o
// getDisplayMedia do Brave devolve um padrão verde falso e ignora --auto-select-tab-capture-*; achado
// no 1º smoke, que gastou uma sessão Live). O resto do caminho (trilha, 1 fps, JPEG 1280) é o real. Custa uma sessão Live por execução: rode com autorização.
//
// WAV com silêncio (uma vez): python -c "import wave;w=wave.open('spike/live/pergunta.wav');p=w.getparams();d=w.readframes(10**9);o=wave.open('pergunta-pad.wav','wb');o.setparams(p);o.writeframes(b'\0'*p.framerate*p.sampwidth*8+d);o.close()"
// Uso: SMOKE_EMAIL=... SMOKE_SENHA=... node scripts/smoke-ligacao-prod.mjs --wav <pergunta-pad.wav> [--base https://chat.toneli.dev.br] [--saida ../.scratch/desafio/screens] [--rotulo 1]
// Latência: fim da fala (último chunk do microfone acima do silêncio) até o 1º chunk de áudio do agente,
// medida no browser (WebSocket embrulhado), então inclui a rede daqui até o servidor.
import { mkdirSync } from 'node:fs'
import path from 'node:path'
import { parseArgs } from 'node:util'
import { chromium } from 'playwright-core'

const BRAVE = 'C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe'
const { values: a } = parseArgs({
  options: {
    wav: { type: 'string' },
    base: { type: 'string', default: 'https://chat.toneli.dev.br' },
    saida: { type: 'string', default: '../.scratch/desafio/screens' },
    rotulo: { type: 'string', default: '1' },
    espera: { type: 'string', default: '60' },
    trace: { type: 'boolean', default: false },
    // Ticket 85: variante de latência (`?v=`): pens0, m31, fq. Vazio = produção.
    v: { type: 'string', default: '' },
    // Segundos de espera fixa (WAV com várias perguntas): não desliga na 1ª resposta.
    fixo: { type: 'string' },
  },
})
const { SMOKE_EMAIL: email, SMOKE_SENHA: senha } = process.env
if (!a.wav || !email || !senha) throw new Error('faltam --wav, SMOKE_EMAIL ou SMOKE_SENHA')
mkdirSync(a.saida, { recursive: true })

async function api(caminho, opcoes = {}) {
  const r = await fetch(`${a.base}${caminho}`, opcoes)
  if (!r.ok) throw new Error(`${caminho}: ${r.status} ${await r.text()}`)
  return r.json()
}
const { access_token: token } = await api('/auth/jwt/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: new URLSearchParams({ username: email, password: senha }),
})
const auth = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
const conv = await api('/api/conversations', { method: 'POST', headers: auth, body: JSON.stringify({ title: `Smoke Ligação ${a.rotulo}` }) })

const browser = await chromium.launch({
  executablePath: BRAVE,
  headless: false,
  args: [
    '--use-fake-device-for-media-stream',
    '--use-fake-ui-for-media-stream',
    `--use-file-for-fake-audio-capture=${path.resolve(a.wav)}%noloop`,
  ],
})
const saida = { conversa: conv.id }
try {
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: 'dark', permissions: ['microphone'] })
  await ctx.addInitScript((t) => {
    localStorage.setItem('tema', 'dark')
    localStorage.setItem('token', t)
  }, token)
  await ctx.addInitScript(() => {
    MediaDevices.prototype.getDisplayMedia = async function () {
      const c = document.createElement('canvas')
      c.width = 1920
      c.height = 1080
      const g = c.getContext('2d')
      const desenhar = () => {
        g.fillStyle = '#ffffff'
        g.fillRect(0, 0, c.width, c.height)
        g.fillStyle = '#111111'
        g.font = 'bold 72px sans-serif'
        g.fillText('Pedido de compra 4827-B', 200, 260)
        g.font = '52px sans-serif'
        g.fillText('Cadeira ergonômica x3: R$ 900,00', 200, 420)
        g.fillText('Monitor 27" x1: R$ 450,90', 200, 520)
        g.font = 'bold 64px sans-serif'
        g.fillText('Total: R$ 1.350,90', 200, 720)
      }
      desenhar()
      setInterval(desenhar, 500)
      return c.captureStream(5)
    }
  })
  // Embrulha o WebSocket da Ligação: tempo de cada chunk enviado (com pico) e recebido.
  await ctx.addInitScript((trace) => {
    window.__trace = trace.trace
    window.__v = trace.v
    const Original = window.WebSocket
    window.__ws = { enviados: [], recebidos: [], textos: [], toques: [], pensando: [] }
    // Ticket 85: instante em que o indicador "pensando" liga e desliga.
    addEventListener('DOMContentLoaded', () => {
      let ligado = false
      new MutationObserver(() => {
        const agora = !!document.querySelector('[data-pensando]')
        if (agora !== ligado) window.__ws.pensando.push({ t: performance.now(), on: (ligado = agora) })
      }).observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ['data-pensando'] })
    })
    const iniciar = AudioBufferSourceNode.prototype.start
    AudioBufferSourceNode.prototype.start = function (...args) {
      window.__ws.toques.push(performance.now())
      return iniciar.apply(this, args)
    }
    window.WebSocket = class extends Original {
      constructor(url, ...args) {
        // Ticket 83: `?trace=1` liga a trilha de latência no servidor (log por marco, sem dado sensível).
        super(String(url).includes('/api/voz/ws') ? `${url}${window.__trace ? '&trace=1' : ''}${window.__v ? `&v=${window.__v}` : ''}` : url, ...args)
        this.addEventListener('message', (e) => {
          if (typeof e.data !== 'string') window.__ws.recebidos.push(performance.now())
          else window.__ws.textos.push({ t: performance.now(), m: JSON.parse(e.data).tipo })
        })
      }
      send(d) {
        if (typeof d !== 'string') {
          const pcm = new Int16Array(d.buffer ? d.buffer.slice(d.byteOffset, d.byteOffset + d.byteLength) : d)
          let pico = 0
          for (const v of pcm) pico = Math.max(pico, Math.abs(v))
          window.__ws.enviados.push({ t: performance.now(), pico })
        }
        super.send(d)
      }
    }
  }, { trace: a.trace, v: a.v })
  const page = await ctx.newPage()
  page.on('pageerror', (e) => console.log(`  [pageerror] ${e.message}`))
  await page.goto(`${a.base}/c/${conv.id}`, { waitUntil: 'networkidle' })
  await page.bringToFront()

  const painel = page.locator('section[aria-label="Ligação"]')
  await page.getByRole('button', { name: 'Iniciar ligação' }).click()
  await painel.waitFor({ state: 'visible' })
  await page.waitForFunction(() => document.querySelector('section[aria-label="Ligação"]')?.getAttribute('data-estado') === 'em_ligacao', null, { timeout: 15000 })
  await page.getByRole('button', { name: 'Compartilhar tela' }).click()
  await page.getByLabel('Prévia da tela compartilhada').waitFor({ timeout: 5000 })
  console.log('em ligação, tela compartilhada; aguardando a pergunta e a resposta')

  const transcricao = page.getByLabel('Transcrição')
  const inicio = Date.now()
  let texto = ''
  while (Date.now() - inicio < Number(a.fixo ?? a.espera) * 1000) {
    texto = await transcricao.innerText()
    if (!a.fixo && texto.includes('Assistente') && /1\.?350/.test(texto)) break
    await page.waitForTimeout(500)
  }
  await page.waitForTimeout(2500)
  texto = await transcricao.innerText()
  await page.screenshot({ path: path.join(a.saida, `80-smoke-${a.rotulo}-prod-1440.png`) })
  await page.getByRole('button', { name: 'Desligar' }).click()
  await page.getByRole('button', { name: 'Iniciar ligação' }).waitFor({ timeout: 15000 })

  const { enviados, recebidos, textos, toques, pensando } = await page.evaluate(() => window.__ws)
  const falou = enviados.filter((e) => e.pico > 500)
  // Uma latência por pergunta: falas separadas por mais de 3 s de silêncio.
  const latencias = []
  const fimsDeFala = []
  falou.forEach((e, i) => {
    if (i + 1 < falou.length && falou[i + 1].t - e.t < 3000) return
    fimsDeFala.push(e.t)
    const r = recebidos.find((t) => t > e.t)
    latencias.push(r ? Math.round(r - e.t) : null)
  })
  const fimFala = falou.at(-1)?.t
  const primeiro = recebidos.find((t) => fimFala && t > fimFala)
  Object.assign(saida, {
    transcricao: texto.replace(/\n+/g, ' | '),
    leuATela: /4827/.test(texto) || /1\.?350/.test(texto),
    chunksMic: enviados.length,
    chunksComFala: falou.length,
    fimFalaAteTranscricaoUsuarioMs: (() => { const t = textos.find((x) => x.m === 'transcricao' && fimFala && x.t > fimFala); return t ? Math.round(t.t - fimFala) : null })(),
    primeiroAudioAteToqueMs: (() => { const t = toques.find((x) => primeiro && x >= primeiro); return t ? Math.round(t - primeiro) : null })(),
    latenciasPorPerguntaMs: latencias,
    // Por pergunta: quanto depois do fim da fala o "pensando" acendeu (browser), e depois do 1º áudio apagou.
    pensandoLigouAposFimFalaMs: fimsDeFala.map((f) => { const p = pensando.find((x) => x.on && x.t > f - 200); return p ? Math.round(p.t - f) : null }),
    latenciaMs: primeiro ? Math.round(primeiro - fimFala) : null,
  })
  const eventos = await api(`/api/audit?event_type=voice_call_ended&conversation_id=${conv.id}`, { headers: auth })
  const lista = eventos.itens ?? eventos.items ?? eventos
  saida.voice_call_ended = lista[0] ? { ...lista[0].payload, custo_micro_usd: lista[0].cost_micro_usd, latency_ms: lista[0].latency_ms } : null
  await ctx.close()
} finally {
  await browser.close()
}
console.log(JSON.stringify(saida, null, 2))
