"""Spike 75: uma sessão Gemini Live com áudio, 1 Frame e transcrição.

Uso (de api/): uv run python ../spike/live/spike_live.py 1280|768 [--fps] [--interromper]
Grava o log de mensagens em spike/live/out/sessao_<res>.jsonl e o áudio em resposta_<res>.wav.
"""

import asyncio, json, sys, time, wave
from pathlib import Path

from google import genai
from google.genai import types

AQUI = Path(__file__).parent
OUT = AQUI / "out"
MODELO = "gemini-3.8-live"
ENV = dict(l.split("=", 1) for l in (AQUI.parents[1] / ".env").read_text().splitlines() if "=" in l and not l.startswith("#"))

CONFIG = types.LiveConnectConfig(
    response_modalities=[types.Modality.AUDIO],
    speech_config=types.SpeechConfig(voice_config=types.VoiceConfig(prebuilt_voice_config=types.PrebuiltVoiceConfig(voice_name="Kore"))),
    input_audio_transcription=types.AudioTranscriptionConfig(),
    output_audio_transcription=types.AudioTranscriptionConfig(),
    context_window_compression=types.ContextWindowCompressionConfig(sliding_window=types.SlidingWindow()),
    # Sessão 1 usou "... Sem tela compartilhada, diga que não vê nada." e o modelo negou ver a tela (RESULTADO.md).
    system_instruction="Você é um assistente de voz. Responda em português brasileiro, curto e falado, sem markdown. "
    "Quando o usuário compartilha a tela, você recebe imagens dela e pode descrevê-las. Se não chegou nenhuma imagem, diga que não vê nada.",
)
CHUNK = 1024  # 32 ms de PCM 16 kHz 16 bits mono


async def falar(s, pcm: bytes, marca: dict, chave: str):
    for i in range(0, len(pcm), CHUNK):
        await s.send_realtime_input(audio=types.Blob(data=pcm[i : i + CHUNK], mime_type="audio/pcm;rate=16000"))
        await asyncio.sleep(0.032)
    marca[chave] = time.perf_counter()


async def tela(s, jpeg: bytes, marca: dict):
    """1 Frame por segundo até o fim da primeira fala (ADR 0028). Conta os Frames para dividir os tokens de IMAGE."""
    while "fim_fala" not in marca:
        await s.send_realtime_input(video=types.Blob(data=jpeg, mime_type="image/jpeg"))
        marca["frames"] = marca.get("frames", 0) + 1
        await asyncio.sleep(1.0)


async def microfone(s, pcm: bytes, marca: dict, interromper: bool, fps: bool):
    """Frame, fala, e silêncio contínuo como um microfone aberto. Com --interromper, repete a fala por cima da resposta."""
    jpeg = (AQUI / f"tela_{marca['res']}.jpg").read_bytes()
    if fps:
        asyncio.create_task(tela(s, jpeg, marca))
    else:  # sessão 1: um Frame só, antes da fala
        await s.send_realtime_input(video=types.Blob(data=jpeg, mime_type="image/jpeg"))
        marca["frames"] = 1
    await asyncio.sleep(0.5)
    await falar(s, pcm, marca, "fim_fala")
    while True:
        if interromper and "primeiro_audio" in marca and "fim_fala2" not in marca:
            await asyncio.sleep(1.0)
            await falar(s, pcm, marca, "fim_fala2")
        await s.send_realtime_input(audio=types.Blob(data=bytes(CHUNK), mime_type="audio/pcm;rate=16000"))
        await asyncio.sleep(0.032)


def anotar(m, marca: dict, audio: bytearray, log, t0: float) -> bool:
    """Guarda áudio e tempos, escreve a mensagem no log sem os bytes. Devolve True no turn_complete."""
    agora, d = time.perf_counter(), m.model_dump(exclude_none=True, mode="json")
    sc = m.server_content
    for p, pd in zip(sc.model_turn.parts, d["server_content"]["model_turn"]["parts"]) if sc and sc.model_turn else []:
        if p.inline_data:
            marca.setdefault("primeiro_audio", agora)
            marca.setdefault("mime", p.inline_data.mime_type)
            audio += p.inline_data.data
            pd["inline_data"]["data"] = f"<{len(p.inline_data.data)} bytes>"
    if sc and sc.output_transcription:
        marca.setdefault("primeira_transcricao", agora)
    log.write(json.dumps({"t": round(agora - t0, 3), **d}, ensure_ascii=False) + "\n")
    return bool(sc and sc.turn_complete)


async def sessao(chave: str, res: str, interromper: bool, fps: bool, marca: dict):
    pcm = wave.open(str(AQUI / "pergunta.wav")).readframes(10**9)
    audio, fim, t0 = bytearray(), False, time.perf_counter()
    with (OUT / f"sessao_{res}.jsonl").open("w", encoding="utf-8") as log:
        async with genai.Client(api_key=chave).aio.live.connect(model=MODELO, config=CONFIG) as s:
            marca["conectou"] = True
            mic = asyncio.create_task(microfone(s, pcm, marca, interromper, fps))
            while not fim:  # com --interromper, espera o turn_complete da resposta à segunda fala
                async for m in s.receive():
                    fim = anotar(m, marca, audio, log, t0) and (not interromper or "fim_fala2" in marca)
            try:  # usage_metadata pode chegar depois do turn_complete
                async with asyncio.timeout(2):
                    async for m in s.receive():
                        anotar(m, marca, audio, log, t0)
            except TimeoutError:
                pass
            mic.cancel()
    with wave.open(str(OUT / f"resposta_{res}.wav"), "wb") as w:
        w.setnchannels(1), w.setsampwidth(2), w.setframerate(24000), w.writeframes(bytes(audio))
    ms = lambda k: round((marca[k] - marca["fim_fala"]) * 1000) if k in marca else None
    print(f"mime={marca.get('mime')} fim_fala->primeiro_audio={ms('primeiro_audio')}ms ->primeira_transcricao={ms('primeira_transcricao')}ms audio_out={len(audio)}B frames={marca.get('frames')} fim_fala_t={marca['fim_fala'] - t0:.3f}s")


async def main():
    res, interromper, fps = sys.argv[1], "--interromper" in sys.argv, "--fps" in sys.argv
    OUT.mkdir(exist_ok=True)
    marca = {"res": res}
    try:
        await asyncio.wait_for(sessao(ENV["GEMINI_API_KEY"], res, interromper, fps, marca), 90)
    except Exception as e:
        print(f"chave free falhou: {type(e).__name__}: {e}")
        if marca.get("conectou"):  # falha no meio da sessão não troca de chave: já gastou uma
            raise
        marca = {"res": res}
        await asyncio.wait_for(sessao(ENV["GEMINI_PAID_API_KEY"], res, interromper, fps, marca), 90)
        print("chave: GEMINI_PAID_API_KEY")
        return
    print("chave: GEMINI_API_KEY")


asyncio.run(main())
