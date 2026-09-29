// Alto-falante da Ligação: fila de chunks PCM16 24 kHz tocados em sequência.
import { TAXA_SAIDA } from './config'

// REVISAR(human): fila de reprodução. Cada chunk vira um AudioBufferSourceNode agendado para
// começar quando o anterior termina (`proximo`), então chunks que chegam em rajada tocam
// colados, sem buraco nem sobreposição. `esvaziar` é o barge-in do lado do browser: no
// `interrompido`, para todas as fontes agendadas na hora. Sem isso o agente seguiria falando
// o áudio que já chegou (segundos) por cima do usuário.
export class FilaAudio {
  private ctx = new AudioContext({ sampleRate: TAXA_SAIDA })
  private fontes = new Set<AudioBufferSourceNode>()
  private proximo = 0
  private aoMudar: (tamanho: number) => void

  /** `aoMudar` recebe quantos chunks faltam tocar: > 0 é o agente falando. */
  constructor(aoMudar: (tamanho: number) => void) {
    this.aoMudar = aoMudar
    void this.ctx.resume()
  }

  tocar(pcm: ArrayBuffer): void {
    // PCM16 little-endian: Int16Array usa a ordem da máquina, little-endian em todo browser comum.
    const amostras = new Int16Array(pcm, 0, pcm.byteLength >> 1)
    if (amostras.length === 0) return
    const buffer = this.ctx.createBuffer(1, amostras.length, TAXA_SAIDA)
    const canal = buffer.getChannelData(0)
    for (let i = 0; i < amostras.length; i++) canal[i] = amostras[i] / 0x8000
    const fonte = this.ctx.createBufferSource()
    fonte.buffer = buffer
    fonte.connect(this.ctx.destination)
    // Fila vazia: começa agora. Senão, emenda no fim do último chunk.
    this.proximo = Math.max(this.proximo, this.ctx.currentTime)
    fonte.start(this.proximo)
    this.proximo += buffer.duration
    fonte.onended = () => {
      this.fontes.delete(fonte)
      this.aoMudar(this.fontes.size)
    }
    this.fontes.add(fonte)
    this.aoMudar(this.fontes.size)
  }

  esvaziar(): void {
    for (const f of this.fontes) {
      f.onended = null
      f.stop()
    }
    this.fontes.clear()
    this.proximo = 0
    this.aoMudar(0)
  }

  fechar(): void {
    this.esvaziar()
    void this.ctx.close()
  }
}
