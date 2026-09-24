// Checagem de rolagem horizontal por rota e largura, no Brave, em dark (ticket 62).
// Aceite dos tickets 63 a 66. Sai com código 1 se alguma rota vaza para a direita.
//
// Uso (no Git Bash, prefixe MSYS_NO_PATHCONV=1 para --rotas não virar caminho do Windows):
//   node scripts/checar-responsivo.mjs --base http://localhost:4180 --saida ../.scratch/desafio/screens \
//     [--email demo@toneli.dev.br] [--senha demo12345] [--rotas /,/config] [--prefixo 62] [--abrir-sidebar]
//
// Rotas com :id e :shareId viram a primeira Conversa e o primeiro link da conta, lidos na API.
// --abrir-sidebar: abaixo de md, abre a sidebar pelo SidebarTrigger e mede de novo.
import { mkdirSync } from 'node:fs'
import path from 'node:path'
import { parseArgs } from 'node:util'
import { chromium } from 'playwright-core'

const BRAVE = 'C:\\Program Files\\BraveSoftware\\Brave-Browser\\Application\\brave.exe'
const LARGURAS = [
  [390, 844],
  [768, 1024],
  [1440, 900],
]
const ROTAS_APP = [
  '/login',
  '/s/:shareId',
  '/',
  '/c/:id',
  '/config',
  '/auditoria',
  '/creditos',
  '/tools',
  '/api-tools',
  '/mcp',
  '/conectores',
  '/compartilhados',
  '/perfil',
  '/admin',
]

const { values: args } = parseArgs({
  options: {
    base: { type: 'string', default: 'http://localhost:4180' },
    email: { type: 'string', default: 'demo@toneli.dev.br' },
    senha: { type: 'string', default: 'demo12345' },
    rotas: { type: 'string' },
    saida: { type: 'string', default: 'screens' },
    prefixo: { type: 'string', default: 'resp' },
    'abrir-sidebar': { type: 'boolean', default: false },
  },
})

const base = args.base.replace(/\/$/, '')
const rotas = args.rotas ? args.rotas.split(',').map((r) => r.trim()) : ROTAS_APP
mkdirSync(args.saida, { recursive: true })

async function entrar() {
  const r = await fetch(`${base}/auth/jwt/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body: new URLSearchParams({ username: args.email, password: args.senha }),
  })
  if (!r.ok) throw new Error(`login falhou: ${r.status}`)
  return (await r.json()).access_token
}

async function primeiro(token, caminho) {
  const r = await fetch(`${base}${caminho}`, { headers: { Authorization: `Bearer ${token}` } })
  const lista = r.ok ? await r.json() : []
  return lista[0] ?? null
}

// Troca os parâmetros da rota por dados reais da conta. null: não há dado, a rota é pulada.
async function resolver(rota, token) {
  if (rota.includes(':id')) {
    const c = await primeiro(token, '/api/conversations')
    return c && rota.replace(':id', c.id)
  }
  if (rota.includes(':shareId')) {
    const s = await primeiro(token, '/api/shares')
    return s && new URL(s.url, base).pathname
  }
  return rota
}

// Roda no browser. Culpado: elemento visível que passa da borda direita e não está dentro de
// container que rola no eixo x. Só o mais externo de cada cadeia é listado.
// overflow-x hidden/clip não isenta: o wrapper do shell tem overflow-hidden e esconderia todo
// conteúdo cortado, que o usuário também não consegue ver. Container que só declarou overflow-y-*
// também não isenta: o CSS promove o x para auto sozinho, e o <main> do shell seria isenção geral
// (docs/DECISOES-AUTONOMAS.md, ticket 62).
function medir() {
  const largura = window.innerWidth
  const soVertical = (el) => {
    const classes = el.getAttribute('class') ?? ''
    return /\boverflow-y-(auto|scroll)\b/.test(classes) && !/\boverflow-(x-)?(auto|scroll)\b/.test(classes)
  }
  const rola = (el) => ['auto', 'scroll'].includes(getComputedStyle(el).overflowX) && !soVertical(el)
  const seletor = (el) => {
    const partes = []
    for (let e = el; e && e !== document.body && partes.length < 4; e = e.parentElement) {
      let p = e.tagName.toLowerCase()
      if (e.id) p += `#${e.id}`
      const slot = e.getAttribute('data-slot')
      if (slot) p += `[data-slot=${slot}]`
      const classes = [...e.classList].filter((c) => !c.includes(':')).slice(0, 3)
      if (classes.length) p += `.${classes.join('.')}`
      partes.unshift(p)
    }
    return partes.join(' > ')
  }
  const vaza = (el) => {
    const r = el.getBoundingClientRect()
    if (r.width === 0 || r.height === 0 || r.right <= largura + 1) return false
    const st = getComputedStyle(el)
    if (st.visibility === 'hidden' || st.display === 'none') return false
    for (let a = el.parentElement; a && a !== document.documentElement; a = a.parentElement) {
      if (a !== document.body && rola(a)) return false
    }
    return true
  }
  const culpados = [...document.body.querySelectorAll('*')].filter(vaza)
  const externos = culpados.filter((el) => !culpados.includes(el.parentElement))
  return {
    scrollWidth: document.documentElement.scrollWidth,
    largura,
    culpados: externos.slice(0, 10).map((el) => ({
      seletor: seletor(el),
      right: Math.round(el.getBoundingClientRect().right),
    })),
  }
}

async function checar(page, rotulo, arquivo) {
  const m = await page.evaluate(medir)
  await page.screenshot({ path: path.join(args.saida, arquivo) })
  const ok = m.scrollWidth <= m.largura && m.culpados.length === 0
  console.log(`${ok ? 'OK  ' : 'FALHA'} ${rotulo} scrollWidth=${m.scrollWidth}`)
  for (const c of m.culpados) console.log(`      right=${c.right} ${c.seletor}`)
  return ok
}

const nomeArquivo = (rota, w, sufixo = '') =>
  `${args.prefixo}-${rota.replace(/^\//, '').replace(/[/:]/g, '_') || 'raiz'}-${w}${sufixo}.png`

const token = await entrar()
const browser = await chromium.launch({ executablePath: BRAVE })
let falhas = 0
try {
  for (const rotaBruta of rotas) {
    const rota = await resolver(rotaBruta, token)
    if (!rota) {
      console.log(`PULA  ${rotaBruta}: a conta não tem dado para o parâmetro`)
      continue
    }
    const publica = rotaBruta === '/login' || rotaBruta.startsWith('/s/')
    for (const [w, h] of LARGURAS) {
      const ctx = await browser.newContext({ viewport: { width: w, height: h }, colorScheme: 'dark' })
      await ctx.addInitScript(
        ([t, pub]) => {
          localStorage.setItem('tema', 'dark')
          if (!pub) localStorage.setItem('token', t)
        },
        [token, publica],
      )
      const page = await ctx.newPage()
      await page.goto(base + rota, { waitUntil: 'networkidle' })
      await page.waitForTimeout(300)
      if (!(await checar(page, `${rota} ${w}`, nomeArquivo(rotaBruta, w)))) falhas++
      const trigger = page.locator('[data-sidebar="trigger"]')
      if (args['abrir-sidebar'] && w < 768 && (await trigger.isVisible())) {
        await trigger.click()
        await page.waitForTimeout(400)
        if (!(await checar(page, `${rota} ${w} sidebar aberta`, nomeArquivo(rotaBruta, w, '-sidebar')))) falhas++
      }
      await ctx.close()
    }
  }
} finally {
  await browser.close()
}
console.log(falhas ? `\n${falhas} violação(ões).` : '\nSem violação.')
process.exit(falhas ? 1 : 0)
