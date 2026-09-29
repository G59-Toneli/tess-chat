"""Servidor da API para o E2E da Ligação (ticket 80): app real, Postgres real, Gemini falso.

Uso: `cd api && PYTHONPATH=. uv run python scripts/servidor_e2e.py [porta]`. Sem chamada real ao Gemini.
O Gemini falso responde a cada 30 chunks de áudio do browser: transcrição do usuário, áudio do
agente (senoide 24 kHz), transcrição acumulada do agente e turn_complete com usage_metadata.
"""

import asyncio
import math
import struct
import sys
from contextlib import asynccontextmanager

import uvicorn
from google.genai import types

from app import voz
from app.main import app

FALA = ["O pedido é o 4827-B, ", "e o total dá R$ 1.350,90."]


def _senoide(segundos: float) -> bytes:
    n = int(24000 * segundos)
    return b"".join(struct.pack("<h", int(math.sin(2 * math.pi * 440 * i / 24000) * 8000)) for i in range(n))


def _msg(**campos) -> types.LiveServerMessage:
    return types.LiveServerMessage(server_content=types.LiveServerContent(**campos))


class GeminiRoteirizado:
    def __init__(self) -> None:
        self.chunks = 0
        self.frames = 0
        self.fila: asyncio.Queue[types.LiveServerMessage] = asyncio.Queue()

    async def send_realtime_input(self, *, audio=None, video=None) -> None:
        if video is not None:
            self.frames += 1
        if audio is not None:
            self.chunks += 1
            if self.chunks % 30 == 0:
                self._turno()

    def _turno(self) -> None:
        m = self.fila.put_nowait
        m(_msg(input_transcription=types.Transcription(text="Qual o total do pedido?")))
        m(_msg(model_turn=types.Content(parts=[types.Part(inline_data=types.Blob(data=_senoide(1.0), mime_type="audio/pcm;rate=24000"))])))
        for pedaco in FALA:
            m(_msg(output_transcription=types.Transcription(text=pedaco)))
        m(
            types.LiveServerMessage(
                server_content=types.LiveServerContent(turn_complete=True),
                usage_metadata=types.UsageMetadata(
                    prompt_tokens_details=[
                        types.ModalityTokenCount(modality="TEXT", token_count=300),
                        types.ModalityTokenCount(modality="AUDIO", token_count=100),
                        types.ModalityTokenCount(modality="IMAGE", token_count=264 if self.frames else 0),
                    ],
                    response_tokens_details=[types.ModalityTokenCount(modality="AUDIO", token_count=25)],
                    thoughts_token_count=0,
                ),
            )
        )

    async def receive(self):
        while True:
            m = await self.fila.get()
            yield m
            if m.server_content and m.server_content.turn_complete:
                return


def _conector():
    @asynccontextmanager
    async def abrir(instrucao: str):
        yield GeminiRoteirizado()

    return abrir


app.dependency_overrides[voz.conectar_gemini] = _conector

if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=int(sys.argv[1]) if len(sys.argv) > 1 else 8018, log_level="warning")
