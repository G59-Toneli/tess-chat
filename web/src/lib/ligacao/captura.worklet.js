// AudioWorklet do microfone. Roda na thread de áudio, fora do React. Carregado por captura.ts com `?url`.

// REVISAR(human): converte o áudio do microfone em PCM16 e junta em chunks de tamanho fixo.
// O AudioContext já roda a 16 kHz (o browser reamostra), então aqui só há float → int16.
// process() recebe 128 amostras por vez; 512 juntas = 32 ms, dentro dos 20 a 40 ms do protocolo.
// Chunk menor gasta mais mensagens no WebSocket; maior atrasa o VAD do Gemini.
// Por que AudioWorklet: roda em tempo real na thread de áudio e entrega PCM cru. O MediaRecorder
// só entrega Opus/WebM comprimido, e o Gemini Live quer PCM.
class CapturaPcm16 extends AudioWorkletProcessor {
  constructor(opcoes) {
    super()
    this.tamanho = opcoes.processorOptions.amostras
    this.buf = new Int16Array(this.tamanho)
    this.n = 0
  }

  process(inputs) {
    const canal = inputs[0] && inputs[0][0]
    if (!canal) return true
    for (let i = 0; i < canal.length; i++) {
      // Float [-1, 1] → int16. Clamp: ganho automático pode passar de 1.
      const s = Math.max(-1, Math.min(1, canal[i]))
      this.buf[this.n++] = s < 0 ? s * 0x8000 : s * 0x7fff
      if (this.n === this.tamanho) {
        // Transfere o buffer (sem cópia) e começa outro.
        this.port.postMessage(this.buf.buffer, [this.buf.buffer])
        this.buf = new Int16Array(this.tamanho)
        this.n = 0
      }
    }
    return true
  }
}

registerProcessor('captura-pcm16', CapturaPcm16)
