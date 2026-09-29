// Teste da Ligação no front (ticket 78) contra um servidor falso que segue docs/PROTOCOLO-LIGACAO.md.
// Sem API real e sem Gemini: o servidor falso responde a API que a tela de Conversa lê, dá o ticket
// e fala o WebSocket da Ligação. Microfone: dispositivo falso do Brave. Tela: canvas no lugar do
// getDisplayMedia (não captura o desktop de quem roda).
//
// Uso (depois de `npm run build`): node scripts/testar-ligacao.mjs [--saida ../.scratch/desafio/screens]
// Sobe o servidor falso na 8078 e o vite preview na 4188 (proxy para a 8078). Sai com 1 se algo falha.
import { spawn } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import http from 'node:http'
import path from 'node:path'
import { parseArgs } from 'node:util'
import { chromium } from 'playwright-core'
import { WebSocketServer } from 'ws'

const BRAVE = 'C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe'
const PORTA_FALSO = 8078
const PORTA_PREVIEW = 4188
const BASE = `http://localhost:${PORTA_PREVIEW}`
const CONV = '7a8b9c0d-1111-4222-8333-944455556666'

const { values: args } = parseArgs({ options: { saida: { type: 'string', default: '../.scratch/desafio/screens' } } })
mkdirSync(args.saida, { recursive: true })

// ---------- servidor falso ----------

const falso = {
  ticket: 200, // status do POST /api/voz/ticket
  fecharCom: null, // close code logo depois do upgrade (4401, 4429...)
  segurarPronto: false, // true: não manda `pronto` até liberarPronto()
  tickets: new Set(),
  ws: null,
  reg: null,
}
const novoRegistro = () => ({ binarios: [], frames: [], json: [], fechou: null })

const agora = () => new Date().toISOString()
const MENSAGENS = [
  { id: 1, role: 'user', parts: [{ type: 'text', text: 'Vou te ligar para revisar um pedido de compra.' }], created_at: agora() },
  { id: 2, role: 'assistant', parts: [{ type: 'text', text: 'Combinado. Quando ligar, compartilhe a tela com o pedido.' }], created_at: agora() },
]

function responder(res, status, corpo) {
  res.writeHead(status, { 'Content-Type': 'application/json' })
  res.end(corpo === undefined ? '' : JSON.stringify(corpo))
}

const api = http.createServer((req, res) => {
  const url = new URL(req.url, 'http://x')
  const p = url.pathname
  if (p === '/auth/jwt/login') return responder(res, 200, { access_token: 'falso', token_type: 'bearer' })
  if (p === '/users/me') return responder(res, 200, { id: 'u1', email: 'demo@toneli.dev.br', is_superuser: false })
  if (p === '/api/conversations')
    return responder(res, 200, [{ id: CONV, title: 'Revisão do pedido 4827-B', created_at: agora(), updated_at: agora() }])
  if (p === `/api/conversations/${CONV}/messages`) return responder(res, 200, MENSAGENS)
  if (p === `/api/conversations/${CONV}/roteador` || p === `/api/conversations/${CONV}/tools`) return responder(res, 200, [])
  if (p.startsWith('/api/chat/') && p.endsWith('/stream')) return responder(res, 204)
  if (p === '/api/voz/ticket' && req.method === 'POST') {
    if (falso.ticket !== 200) return responder(res, falso.ticket, { detail: 'recusado pelo falso' })
    const t = `t-${Math.random().toString(36).slice(2)}`
    falso.tickets.add(t)
    return responder(res, 200, { ticket: t, expira_em: 30 })
  }
  return responder(res, 404, { detail: 'Not Found' })
})

const wss = new WebSocketServer({ noServer: true })
api.on('upgrade', (req, sock, head) => {
  const url = new URL(req.url, 'http://x')
  if (url.pathname !== '/api/voz/ws') return sock.destroy()
  wss.handleUpgrade(req, sock, head, (ws) => {
    const ticket = url.searchParams.get('ticket')
    // Uso único, como o protocolo.
    if (!falso.tickets.delete(ticket)) return ws.close(4401)
    if (falso.fecharCom) return ws.close(falso.fecharCom)
    const reg = novoRegistro()
    falso.ws = ws
    falso.reg = reg
    ws.on('message', (data, binario) => {
      const t = Date.now()
      if (binario) return reg.binarios.push({ t, bytes: data.length })
      const m = JSON.parse(data.toString())
      reg.json.push({ t, ...m, jpeg: undefined })
      if (m.tipo === 'frame') reg.frames.push({ t, jpeg: Buffer.from(m.jpeg, 'base64') })
      if (m.tipo === 'desligar' && ws.readyState === ws.OPEN) {
        ws.send(JSON.stringify({ tipo: 'fim', motivo: 'desligou' }))
        ws.close(1000)
      }
    })
    ws.on('close', (codigo) => (reg.fechou = { t: Date.now(), codigo }))
    if (!falso.segurarPronto) liberarPronto()
  })
})

function liberarPronto() {
  falso.ws?.send(JSON.stringify({ tipo: 'pronto', limite_s: 540 }))
}
const mandar = (m) => falso.ws.send(JSON.stringify(m))

/** Áudio do agente: senoide PCM16 24 kHz, em chunks de 200 ms, tudo de uma vez (rajada, como o Gemini). */
function mandarAudio(segundos) {
  const porChunk = 24000 * 0.2
  for (let c = 0; c < segundos / 0.2; c++) {
    const buf = Buffer.alloc(porChunk * 2)
    for (let i = 0; i < porChunk; i++) buf.writeInt16LE(Math.round(Math.sin((2 * Math.PI * 440 * (c * porChunk + i)) / 24000) * 8000), i * 2)
    falso.ws.send(buf)
  }
}

/** Largura e altura do JPEG, do marcador SOF0/SOF2. */
function dimensoesJpeg(b) {
  if (b[0] !== 0xff || b[1] !== 0xd8) return null
  let i = 2
  while (i < b.length) {
    const marcador = b[i + 1]
    const tam = b.readUInt16BE(i + 2)
    if (marcador === 0xc0 || marcador === 0xc2) return { h: b.readUInt16BE(i + 5), w: b.readUInt16BE(i + 7) }
    i += 2 + tam
  }
  return null
}

// ---------- browser ----------

// Tela falsa: um pedido de compra desenhado num canvas 1920x1080, redesenhado a cada 500 ms.
function telaFalsa() {
  MediaDevices.prototype.getDisplayMedia = async function () {
    const c = document.createElement('canvas')
    c.width = 1920
    c.height = 1080
    const g = c.getContext('2d')
    const desenhar = () => {
      g.fillStyle = '#f4f4f5'
      g.fillRect(0, 0, c.width, c.height)
      g.fillStyle = '#ffffff'
      g.fillRect(360, 80, 1200, 920)
      g.fillStyle = '#18181b'
      g.font = 'bold 64px sans-serif'
      g.fillText('Pedido de compra 4827-B', 440, 220)
      g.font = '40px sans-serif'
      const linhas = ['Cadeira ergonômica  x3   R$ 900,00', 'Monitor 27"            x1   R$ 450,90', 'Frete                             R$ 0,00']
      linhas.forEach((l, i) => g.fillText(l, 440, 360 + i * 80))
      g.font = 'bold 52px sans-serif'
      g.fillText('Total: R$ 1.350,90', 440, 700)
      g.font = '28px sans-serif'
      g.fillStyle = '#71717a'
      g.fillText(new Date().toLocaleTimeString('pt-BR'), 440, 920)
    }
    desenhar()
    setInterval(desenhar, 500)
    const s = c.captureStream(5)
    window.__trilhaTela = s.getVideoTracks()[0]
    return s
  }
}

const falhas = []
function checar(ok, rotulo, detalhe = '') {
  console.log(`${ok ? 'OK   ' : 'FALHA'} ${rotulo}${detalhe ? `  (${detalhe})` : ''}`)
  if (!ok) falhas.push(rotulo)
}
const esperar = (ms) => new Promise((r) => setTimeout(r, ms))
const tela = (nome) => path.join(args.saida, `78-${nome}.png`)

async function novaPagina(browser, [w, h], { semTela = false } = {}) {
  const ctx = await browser.newContext({ viewport: { width: w, height: h }, colorScheme: 'dark', permissions: ['microphone'] })
  await ctx.addInitScript(() => {
    localStorage.setItem('tema', 'dark')
    localStorage.setItem('token', 'falso')
  })
  await ctx.addInitScript(semTela ? () => delete MediaDevices.prototype.getDisplayMedia : telaFalsa)
  const page = await ctx.newPage()
  page.on('pageerror', (e) => console.log(`  [pageerror] ${e.message}`))
  await page.goto(`${BASE}/c/${CONV}`, { waitUntil: 'networkidle' })
  return page
}

const painel = (page) => page.locator('section[aria-label="Ligação"]')
const estado = (page) => painel(page).getAttribute('data-estado')
async function ate(fn, ms = 5000) {
  const fim = Date.now() + ms
  while (Date.now() < fim) {
    if (await fn()) return true
    await esperar(50)
  }
  return false
}

async function cenarioPrincipal(browser) {
  console.log('\n# 1440x900: conectando, áudio, frames, transcrição, barge-in, desligar')
  falso.segurarPronto = true
  const page = await novaPagina(browser, [1440, 900])
  await page.getByRole('button', { name: 'Iniciar ligação' }).click()
  checar(await ate(async () => (await estado(page)) === 'conectando' && falso.ws), 'painel em conectando até o pronto')
  await page.waitForTimeout(300)
  await page.screenshot({ path: tela('conectando-1440') })
  liberarPronto()
  checar(await ate(async () => (await estado(page)) === 'em_ligacao'), 'pronto → em ligação')
  checar(await page.getByLabel('Mensagem').isDisabled(), 'input de texto desabilitado na Ligação')

  await page.waitForTimeout(1500)
  const bin = falso.reg.binarios
  const tamanhos = [...new Set(bin.map((b) => b.bytes))]
  checar(bin.length >= 20 && bin.every((b) => b.bytes >= 640 && b.bytes <= 1280), 'áudio sai binário em chunks de 20 a 40 ms', `${bin.length} chunks, bytes ${tamanhos.join(',')}`)
  checar(!falso.reg.json.some((m) => m.tipo === 'audio'), 'áudio não vai como JSON')

  await page.getByRole('button', { name: 'Compartilhar tela' }).click()
  checar(await ate(async () => falso.reg.json.some((m) => m.tipo === 'tela' && m.ativa === true)), 'tela ativa:true enviado')
  await page.waitForTimeout(5500)
  const fr = falso.reg.frames
  const intervalos = fr.slice(1).map((f, i) => f.t - fr[i].t)
  const dims = fr.map((f) => dimensoesJpeg(f.jpeg))
  checar(fr.length >= 4 && fr.length <= 6, 'Frames a 1 fps', `${fr.length} em 5,5 s, intervalos ${intervalos.join(',')} ms`)
  checar(intervalos.every((d) => d >= 800 && d <= 1250), 'intervalo entre Frames perto de 1 s')
  checar(dims.every((d) => d && d.w === 1280 && d.h === 720), 'Frame JPEG com lado maior 1280', JSON.stringify(dims[0]))
  checar(await page.getByLabel('Prévia da tela compartilhada').isVisible(), 'prévia da tela no painel')

  mandar({ tipo: 'transcricao', origem: 'usuario', texto: 'Lê pra mim o número do pedido e o total.', final: true })
  // Texto acumulado, como o api/app/voz.py manda.
  for (const ate of ['O número do pedido', 'O número do pedido é 4827-B, e o total', 'O número do pedido é 4827-B, e o total dá R$ 1.350,90.']) {
    mandar({ tipo: 'transcricao', origem: 'agente', texto: ate, final: false })
    await esperar(80)
  }
  mandarAudio(4)
  checar(await ate(async () => Number(await painel(page).getAttribute('data-fila')) > 0, 2000), 'áudio do agente entra na fila')
  checar(await page.locator('[data-falando]').isVisible(), 'Assistente aparece falando')
  await page.waitForTimeout(400)
  const linhas = await page.getByLabel('Transcrição').locator('p').allInnerTexts()
  checar(linhas.length === 2 && linhas[1].endsWith('O número do pedido é 4827-B, e o total dá R$ 1.350,90.'), 'transcrição ao vivo troca o texto acumulado', JSON.stringify(linhas))
  await page.screenshot({ path: tela('em-ligacao-1440') })

  const antes = Number(await painel(page).getAttribute('data-fila'))
  mandar({ tipo: 'interrompido' })
  checar(await ate(async () => Number(await painel(page).getAttribute('data-fila')) === 0, 300), 'interrompido esvazia a fila na hora', `fila antes ${antes}`)
  mandar({ tipo: 'transcricao', origem: 'agente', texto: 'O número do pedido é 4827-B, e o total dá R$ 1.350,90.', final: true })
  await page.waitForTimeout(200)
  checar((await page.getByLabel('Transcrição').locator('p').count()) === 2, 'final do turno cortado não duplica a fala')

  // "Parar de compartilhar" da barra do browser: a trilha termina sozinha.
  await page.evaluate(() => window.__trilhaTela.dispatchEvent(new Event('ended')))
  checar(await ate(async () => falso.reg.json.some((m) => m.tipo === 'tela' && m.ativa === false), 1000), 'fim pela barra do browser manda tela:false')
  const nFrames = falso.reg.frames.length
  await page.waitForTimeout(2200)
  checar(falso.reg.frames.length === nFrames, 'Frames param com a trilha encerrada')

  await page.getByRole('button', { name: 'Desligar' }).click()
  checar(await ate(async () => falso.reg.json.some((m) => m.tipo === 'desligar')), 'desligar enviado')
  checar(await ate(async () => page.getByRole('button', { name: 'Iniciar ligação' }).isVisible()), 'painel fecha depois do fim')
  checar(!(await page.getByLabel('Mensagem').isDisabled()), 'input volta depois da Ligação')

  // Sair da Conversa pela sidebar desmonta o painel: microfone, tela e WebSocket fecham.
  falso.segurarPronto = false
  await page.getByRole('button', { name: 'Iniciar ligação' }).click()
  checar(await ate(async () => (await estado(page)) === 'em_ligacao'), 'segunda Ligação conecta')
  const reg = falso.reg
  await page.locator('a[href="/config"]').first().click()
  checar(await ate(async () => reg.fechou !== null, 2000), 'desmontar a tela fecha o WebSocket', `code ${reg.fechou?.codigo}`)
  checar(reg.json.some((m) => m.tipo === 'desligar'), 'desmontar manda desligar antes de fechar')
  await page.context().close()
}

async function cenarioMobile(browser) {
  console.log('\n# 390x844: painel em ligação com tela e transcrição')
  const page = await novaPagina(browser, [390, 844])
  await page.getByRole('button', { name: 'Iniciar ligação' }).click()
  await ate(async () => (await estado(page)) === 'em_ligacao')
  await page.getByRole('button', { name: 'Compartilhar tela' }).click()
  await page.waitForTimeout(1200)
  mandar({ tipo: 'transcricao', origem: 'usuario', texto: 'Qual é o total?', final: true })
  mandar({ tipo: 'transcricao', origem: 'agente', texto: 'O total é R$ 1.350,90.', final: true })
  mandarAudio(3)
  await page.waitForTimeout(400)
  const m = await page.evaluate(() => ({ sw: document.documentElement.scrollWidth, w: innerWidth }))
  checar(m.sw <= m.w, 'sem rolagem horizontal em 390', `scrollWidth ${m.sw}`)
  await page.screenshot({ path: tela('em-ligacao-390') })
  await page.context().close()
}

async function cenarioErros(browser) {
  console.log('\n# erros: 402 no ticket, 4429 no WebSocket, sem getDisplayMedia')
  falso.ticket = 402
  let page = await novaPagina(browser, [1440, 900])
  await page.getByRole('button', { name: 'Iniciar ligação' }).click()
  const alerta = painel(page).getByRole('alert')
  checar(await ate(() => alerta.isVisible()), 'erro 402 aparece')
  checar((await alerta.innerText()).includes('crédito') && (await page.getByRole('link', { name: 'Ver créditos' }).isVisible()), '402 com texto de crédito e link')
  await page.screenshot({ path: tela('erro-402-1440') })
  checar(!(await page.getByLabel('Mensagem').isDisabled()), 'no erro o input de texto volta')
  await page.context().close()
  falso.ticket = 200

  falso.fecharCom = 4429
  page = await novaPagina(browser, [1440, 900])
  await page.getByRole('button', { name: 'Iniciar ligação' }).click()
  checar(await ate(async () => (await estado(page)) === 'erro'), 'close 4429 vira erro')
  checar(await painel(page).getByText('Muitas ligações ao mesmo tempo').isVisible(), '4429 com texto legível')
  falso.fecharCom = null
  await painel(page).getByRole('button', { name: 'Tentar de novo' }).click()
  checar(await ate(async () => (await estado(page)) === 'em_ligacao'), 'tentar de novo conecta')
  await page.context().close()

  page = await novaPagina(browser, [1440, 900], { semTela: true })
  await page.getByRole('button', { name: 'Iniciar ligação' }).click()
  await ate(async () => (await estado(page)) === 'em_ligacao')
  checar((await page.getByRole('button', { name: 'Compartilhar tela' }).count()) === 0, 'sem getDisplayMedia o botão some')
  await page.context().close()
}

// ---------- execução ----------

await new Promise((r) => api.listen(PORTA_FALSO, r))
const preview = spawn(process.execPath, ['node_modules/vite/bin/vite.js', 'preview', '--port', String(PORTA_PREVIEW), '--strictPort'], {
  env: { ...process.env, API_URL: `http://localhost:${PORTA_FALSO}` },
  stdio: 'ignore',
})
const browser = await chromium.launch({
  executablePath: BRAVE,
  args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream'],
})
try {
  if (!(await ate(() => fetch(BASE).then((r) => r.ok, () => false), 15000))) throw new Error('vite preview não subiu')
  await cenarioPrincipal(browser)
  await cenarioMobile(browser)
  await cenarioErros(browser)
} catch (e) {
  console.error(e)
  falhas.push(String(e))
} finally {
  await browser.close()
  preview.kill()
  wss.close()
  api.close()
}
console.log(falhas.length ? `\n${falhas.length} falha(s).` : '\nTudo passou.')
process.exit(falhas.length ? 1 : 0)
