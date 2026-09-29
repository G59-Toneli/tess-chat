// E2E da Ligação (ticket 80) sem custo: browser real, front buildado, API real (Postgres real) com
// Gemini roteirizado (api/scripts/servidor_e2e.py). Microfone: dispositivo falso do Brave. Tela: canvas
// no lugar do getDisplayMedia.
//
// Pré-requisitos: Postgres do compose de pé, `npm run build`, e a API falsa na 8018:
//   (cd ../api && PYTHONPATH=. uv run python scripts/servidor_e2e.py 8018)
// Uso: node scripts/e2e-ligacao.mjs [--saida ../.scratch/desafio/screens]
// Sobe o vite preview na 4191 (proxy para a 8018). Sai com 1 se algo falha.
import { spawn } from 'node:child_process'
import { mkdirSync } from 'node:fs'
import path from 'node:path'
import { parseArgs } from 'node:util'
import { chromium } from 'playwright-core'

const BRAVE = 'C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe'
const PORTA_API = 8018
const PORTA_PREVIEW = 4191
const BASE = `http://localhost:${PORTA_PREVIEW}`
const API = `http://localhost:${PORTA_API}`

const { values: args } = parseArgs({ options: { saida: { type: 'string', default: '../.scratch/desafio/screens' } } })
mkdirSync(args.saida, { recursive: true })

const falhas = []
function checar(ok, rotulo, detalhe = '') {
  console.log(`${ok ? 'OK   ' : 'FALHA'} ${rotulo}${detalhe ? `  (${detalhe})` : ''}`)
  if (!ok) falhas.push(rotulo)
}
const esperar = (ms) => new Promise((r) => setTimeout(r, ms))
async function ate(fn, ms = 8000) {
  const fim = Date.now() + ms
  while (Date.now() < fim) {
    if (await fn()) return true
    await esperar(100)
  }
  return false
}

/** Tela falsa: pedido de compra num canvas, redesenhado a cada 500 ms. */
function telaFalsa() {
  MediaDevices.prototype.getDisplayMedia = async function () {
    const c = document.createElement('canvas')
    c.width = 1920
    c.height = 1080
    const g = c.getContext('2d')
    const desenhar = () => {
      g.fillStyle = '#ffffff'
      g.fillRect(0, 0, c.width, c.height)
      g.fillStyle = '#18181b'
      g.font = 'bold 64px sans-serif'
      g.fillText('Pedido de compra 4827-B', 440, 220)
      g.font = 'bold 52px sans-serif'
      g.fillText('Total: R$ 1.350,90', 440, 700)
    }
    desenhar()
    setInterval(desenhar, 500)
    return c.captureStream(5)
  }
}

async function json(caminho, opcoes = {}) {
  const r = await fetch(`${API}${caminho}`, opcoes)
  if (!r.ok) throw new Error(`${caminho}: ${r.status} ${await r.text()}`)
  return r.json()
}

// ---------- prepara conta e Conversa pela API ----------
const email = `e2e-${Date.now()}@toneli.dev.br`
const senha = 'e2e-senha-12345'
await json('/auth/register', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ email, password: senha }) })
const { access_token: token } = await json('/auth/jwt/login', {
  method: 'POST',
  headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  body: new URLSearchParams({ username: email, password: senha }),
})
const auth = { Authorization: `Bearer ${token}`, 'Content-Type': 'application/json' }
const conv = await json('/api/conversations', { method: 'POST', headers: auth, body: JSON.stringify({ title: 'E2E da Ligação' }) })

const preview = spawn(process.execPath, ['node_modules/vite/bin/vite.js', 'preview', '--port', String(PORTA_PREVIEW), '--strictPort'], {
  env: { ...process.env, API_URL: API },
  stdio: 'ignore',
})
const browser = await chromium.launch({
  executablePath: BRAVE,
  // Microfone: WAV pt-BR (7,3 s de fala, SAPI) uma vez; o Gemini falso responde depois do silêncio.
  args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream', `--use-file-for-fake-audio-capture=${path.resolve('../spike/live/pergunta.wav')}%noloop`],
})
try {
  if (!(await ate(() => fetch(BASE).then((r) => r.ok, () => false), 15000))) throw new Error('vite preview não subiu')
  const ctx = await browser.newContext({ viewport: { width: 1440, height: 900 }, colorScheme: 'dark', permissions: ['microphone'] })
  await ctx.addInitScript((t) => {
    localStorage.setItem('tema', 'dark')
    localStorage.setItem('token', t)
  }, token)
  await ctx.addInitScript(telaFalsa)
  // Ticket 85: registra se o indicador "pensando" (data-pensando) apareceu em algum momento.
  await ctx.addInitScript(() => {
    window.__pensou = false
    addEventListener('DOMContentLoaded', () => {
      new MutationObserver(() => {
        if (document.querySelector('[data-pensando]')) window.__pensou = true
      }).observe(document.body, { subtree: true, childList: true, attributes: true, attributeFilter: ['data-pensando'] })
    })
  })
  const page = await ctx.newPage()
  page.on('pageerror', (e) => console.log(`  [pageerror] ${e.message}`))
  await page.goto(`${BASE}/c/${conv.id}`, { waitUntil: 'networkidle' })

  const painel = page.locator('section[aria-label="Ligação"]')
  await page.getByRole('button', { name: 'Iniciar ligação' }).click()
  checar(await ate(async () => (await painel.getAttribute('data-estado')) === 'em_ligacao'), 'liga: painel em ligação (ticket, WebSocket, pronto)')

  await page.getByRole('button', { name: 'Compartilhar tela' }).click()
  checar(await ate(() => page.getByLabel('Prévia da tela compartilhada').isVisible(), 3000), 'compartilhar tela: prévia visível')

  const transcricao = page.getByLabel('Transcrição')
  checar(await ate(async () => (await transcricao.innerText()).includes('R$ 1.350,90.'), 15000), 'transcrição do agente chega inteira', (await transcricao.innerText()).replace(/\n+/g, ' | '))
  checar((await transcricao.innerText()).includes('Qual o total do pedido?'), 'transcrição do usuário chega')
  checar(await ate(async () => Number(await painel.getAttribute('data-fila')) > 0 || (await page.locator('[data-falando]').count()) > 0, 3000), 'áudio do agente chegou ao player')
    checar(await page.evaluate(() => window.__pensou), 'pensando: o indicador acende depois que a fala do usuário para (WAV falado, depois silêncio)')
  await page.screenshot({ path: path.join(args.saida, '80-e2e-em-ligacao-1440.png') })

  await page.getByRole('button', { name: 'Desligar' }).click()
  checar(await ate(() => page.getByRole('button', { name: 'Iniciar ligação' }).isVisible()), 'desligar: painel fecha')

  // Histórico: as falas da Ligação viram Mensagens da Conversa.
  await page.reload({ waitUntil: 'networkidle' })
  const corpo = await page.locator('main').innerText()
  checar(corpo.includes('Qual o total do pedido?') && corpo.includes('R$ 1.350,90'), 'histórico: falas da Ligação na Conversa depois de recarregar')
  await page.screenshot({ path: path.join(args.saida, '80-e2e-historico-1440.png') })

  // Auditoria: voice_call_ended com tela e crédito.
  const eventos = await json(`/api/audit?event_type=voice_call_ended&conversation_id=${conv.id}`, { headers: auth })
  const ev = eventos.itens?.[0] ?? eventos.items?.[0] ?? eventos[0]
  checar(!!ev, 'auditoria: voice_call_ended emitido', ev ? `motivo ${ev.payload.motivo}, custo ${ev.cost_micro_usd} micro-USD` : JSON.stringify(eventos).slice(0, 200))
  checar(ev?.payload.motivo === 'desligou' && ev.cost_micro_usd > 0, 'auditoria: motivo desligou e custo > 0')
  await page.goto(`${BASE}/auditoria?tipo=voice_call_ended`, { waitUntil: 'networkidle' })
  await page.waitForTimeout(500)
  checar((await page.locator('table').count()) > 0 && (await page.locator('tbody tr').count()) >= 1, '/auditoria mostra o evento na tela')
  await page.screenshot({ path: path.join(args.saida, '80-e2e-auditoria-1440.png') })
  await ctx.close()
} catch (e) {
  console.error(e)
  falhas.push(String(e))
} finally {
  await browser.close()
  preview.kill()
}
console.log(falhas.length ? `\n${falhas.length} falha(s).` : '\nTudo passou.')
process.exit(falhas.length ? 1 : 0)
