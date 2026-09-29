// Tela compartilhada → Frames JPEG em base64, a 1 fps (ADR 0028).
import { FPS_TELA, LADO_MAIOR, QUALIDADE_JPEG } from './config'

export type Tela = {
  stream: MediaStream
  parar: () => void
}

/** Celular não tem getDisplayMedia: o botão de compartilhar some. */
export const suportaTela = () => typeof navigator.mediaDevices?.getDisplayMedia === 'function'

// REVISAR(human): laço de Frames. A cada 1/FPS s desenha o quadro atual do vídeo num canvas
// reduzido (lado maior até 1280, sem ampliar) e codifica em JPEG 0,7. `ocupado` pula o tique se
// o JPEG anterior ainda não saiu, para não empilhar Frames atrasados. 1 fps basta: o caso de
// uso é documento, código e slide, que mudam pouco por segundo, e a Live API não aceita mais.
// `onended` da trilha cobre o "Parar de compartilhar" da barra do browser.
// Ressalva: com a aba do app escondida por mais de 5 min, o Chrome pode espaçar o setInterval.
export async function compartilharTela(aoFrame: (jpeg: string) => void, aoTerminar: () => void): Promise<Tela> {
  const stream = await navigator.mediaDevices.getDisplayMedia({ video: true, audio: false })
  const video = document.createElement('video')
  video.muted = true
  video.srcObject = stream
  await video.play().catch(() => undefined)
  const canvas = document.createElement('canvas')
  let ocupado = false
  const timer = setInterval(async () => {
    if (ocupado || !video.videoWidth) return
    ocupado = true
    try {
      const jpeg = await capturar(video, canvas)
      if (jpeg) aoFrame(jpeg)
    } finally {
      ocupado = false
    }
  }, 1000 / FPS_TELA)

  let parado = false
  const parar = () => {
    if (parado) return
    parado = true
    clearInterval(timer)
    stream.getTracks().forEach((t) => t.stop())
    video.srcObject = null
  }
  stream.getVideoTracks()[0]?.addEventListener('ended', () => {
    if (parado) return
    parar()
    aoTerminar()
  })
  return { stream, parar }
}

async function capturar(video: HTMLVideoElement, canvas: HTMLCanvasElement): Promise<string | null> {
  const escala = Math.min(1, LADO_MAIOR / Math.max(video.videoWidth, video.videoHeight))
  canvas.width = Math.round(video.videoWidth * escala)
  canvas.height = Math.round(video.videoHeight * escala)
  canvas.getContext('2d')?.drawImage(video, 0, 0, canvas.width, canvas.height)
  const blob = await new Promise<Blob | null>((r) => canvas.toBlob(r, 'image/jpeg', QUALIDADE_JPEG))
  if (!blob) return null
  const bytes = new Uint8Array(await blob.arrayBuffer())
  let bin = ''
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode(...bytes.subarray(i, i + 0x8000))
  return btoa(bin)
}
