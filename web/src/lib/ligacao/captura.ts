// Microfone → chunks PCM16 16 kHz. A conversão fica no worklet (captura.worklet.js).
// no-inline: arquivo próprio em vez de data: URL (worklet em data: pode esbarrar em CSP).
import urlWorklet from './captura.worklet.js?url&no-inline'
import { AMOSTRAS_POR_CHUNK, TAXA_ENTRADA } from './config'

export type Microfone = {
  mutar: (mudo: boolean) => void
  parar: () => void
}

/** Lança o erro do getUserMedia (permissão negada, sem microfone). Quem chama traduz. */
export async function abrirMicrofone(aoChunk: (pcm: ArrayBuffer) => void): Promise<Microfone> {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
  })
  // Contexto a 16 kHz: o browser reamostra a entrada do microfone.
  const ctx = new AudioContext({ sampleRate: TAXA_ENTRADA })
  try {
    await ctx.audioWorklet.addModule(urlWorklet)
  } catch (e) {
    stream.getTracks().forEach((t) => t.stop())
    void ctx.close()
    throw e
  }
  const fonte = ctx.createMediaStreamSource(stream)
  const no = new AudioWorkletNode(ctx, 'captura-pcm16', { processorOptions: { amostras: AMOSTRAS_POR_CHUNK } })
  no.port.onmessage = (e: MessageEvent<ArrayBuffer>) => aoChunk(e.data)
  // O worklet não escreve na saída: ligar no destination só mantém o nó puxado, sem eco.
  fonte.connect(no).connect(ctx.destination)
  void ctx.resume()
  return {
    // Mudo: a trilha manda zeros. O servidor segue recebendo silêncio e o VAD fecha a fala.
    mutar: (mudo) => stream.getAudioTracks().forEach((t) => (t.enabled = !mudo)),
    parar: () => {
      no.port.onmessage = null
      stream.getTracks().forEach((t) => t.stop())
      void ctx.close()
    },
  }
}
