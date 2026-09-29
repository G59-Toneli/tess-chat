// Sonda sem custo (ticket 83): o microfone falso do Brave com WAV %noloop segue mandando chunks de silêncio
// depois do fim do arquivo? Abre só uma página estática, sem Ligação, sem Gemini.
// Uso: node scripts/sonda-mic-falso.mjs <wav> [--base https://chat.toneli.dev.br]
import path from 'node:path'
import { chromium } from 'playwright-core'

const BRAVE = 'C:/Program Files/BraveSoftware/Brave-Browser/Application/brave.exe'
const wav = path.resolve(process.argv[2])
const base = process.argv[3] ?? 'https://chat.toneli.dev.br'
const browser = await chromium.launch({
  executablePath: BRAVE,
  headless: false,
  args: ['--use-fake-device-for-media-stream', '--use-fake-ui-for-media-stream', `--use-file-for-fake-audio-capture=${wav}%noloop`],
})
try {
  const ctx = await browser.newContext({ permissions: ['microphone'] })
  const page = await ctx.newPage()
  await page.goto(base, { waitUntil: 'domcontentloaded' })
  const chunks = await page.evaluate(async () => {
    const stream = await navigator.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 } })
    const ac = new AudioContext({ sampleRate: 16000 })
    const no = ac.createScriptProcessor(512, 1, 1)
    const saida = []
    no.onaudioprocess = (e) => {
      const c = e.inputBuffer.getChannelData(0)
      let pico = 0
      for (const v of c) pico = Math.max(pico, Math.abs(v * 32767))
      saida.push({ t: performance.now(), pico })
    }
    ac.createMediaStreamSource(stream).connect(no).connect(ac.destination)
    await ac.resume()
    await new Promise((r) => setTimeout(r, 22000))
    return saida
  })
  const altos = chunks.filter((c) => c.pico > 500)
  const fim = altos.at(-1)
  const depois = chunks.filter((c) => c.t > fim.t)
  const gaps = chunks.slice(1).map((c, i) => c.t - chunks[i].t)
  console.log(JSON.stringify({
    chunks: chunks.length,
    altos: altos.length,
    duracaoComFalaMs: Math.round(fim.t - altos[0].t),
    chunksDepoisDoFim: depois.length,
    msDepoisDoFimAteUltimoChunk: Math.round(chunks.at(-1).t - fim.t),
    picoMaxDepoisDoFim: Math.max(...depois.map((c) => c.pico)),
    gapMaxMs: Math.round(Math.max(...gaps)),
    // Pico máximo por janela de 200 ms depois do último chunk alto: mostra o quão silencioso é o "silêncio".
    piscoPorJanela200ms: Array.from({ length: 15 }, (_, i) => Math.round(Math.max(0, ...depois.filter((c) => c.t - fim.t >= i * 200 && c.t - fim.t < (i + 1) * 200).map((c) => c.pico)))),
  }, null, 1))
} finally {
  await browser.close()
}
