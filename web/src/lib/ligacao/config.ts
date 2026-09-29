// Parâmetros da Ligação no browser. Contrato em docs/PROTOCOLO-LIGACAO.md; valores do ADR 0028 e do spike 75.

/** Microfone → servidor: PCM16 mono a 16 kHz. */
export const TAXA_ENTRADA = 16000
/** 512 amostras a 16 kHz = 32 ms = 1024 bytes por chunk (o protocolo pede 20 a 40 ms). */
export const AMOSTRAS_POR_CHUNK = 512
/** Servidor → alto-falante: PCM16 mono a 24 kHz. */
export const TAXA_SAIDA = 24000

/** Frame da tela: 1 por segundo, JPEG 0,7, lado maior até 1280 px (spike: 264 tokens a 1280 e a 768). */
export const FPS_TELA = 1
export const QUALIDADE_JPEG = 0.7
export const LADO_MAIOR = 1280

/** Limite da Ligação até o `pronto` dizer o dele. */
export const LIMITE_PADRAO_S = 540

/** "Pensando": pico de amostra acima disto é fala, e este silêncio depois da fala acende o indicador (ticket 85). */
export const PICO_FALA = 500
export const SILENCIO_LOCAL_MS = 400
/** O indicador apaga sozinho se o agente não falar (fala partida, ruído). */
export const PENSANDO_MAX_MS = 10000
