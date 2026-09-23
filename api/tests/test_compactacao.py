"""Compactação do histórico (ticket 12, ADR 0006). Modelo principal e resumidor são FunctionModel."""

import json
from contextlib import asynccontextmanager

from pydantic_ai.messages import ModelMessage, ModelRequest, ToolCallPart, ToolReturnPart, UserPromptPart
from pydantic_ai.models.function import AgentInfo, DeltaToolCall, FunctionModel
from pydantic_ai.usage import RequestUsage, RunUsage
from sqlalchemy import select

from app.chat import MODELO
from app.compactacao import MODELO_RESUMO, should_compact
from app.config import Settings, settings
from app.credito import CreditLedger
from app.db import SessionLocal
from tests.test_auth import eventos
from tests.test_chat import corpo
from tests.test_conversas import criar, usuario
from tests.test_tools import Rotas

LONGO = " ".join(["palavra"] * 900)
RESUMO = "RESUMO: o usuário se chama Ana e gosta de xadrez."


class ComUso(FunctionModel):
    """FunctionModel em stream reporta input fixo. Aqui o input é 1 token por palavra do histórico, como um provedor."""

    @asynccontextmanager
    async def request_stream(self, messages, *args, **kwargs):
        async with super().request_stream(messages, *args, **kwargs) as resp:
            resp._usage = RequestUsage(input_tokens=len(conteudos(messages).split()))
            yield resp


def conteudos(msgs: list[ModelMessage]) -> str:
    return str([getattr(p, "content", None) for m in msgs for p in m.parts])


def modelo_eco(vistas: list[list[ModelMessage]]) -> FunctionModel:
    async def stream(msgs: list[ModelMessage], _info: AgentInfo):
        vistas.append(msgs)
        yield f"resposta {len(vistas)}"

    return ComUso(stream_function=stream, model_name=MODELO)


def test_should_compact_so_acima_do_limiar():
    s = Settings(compactacao_limiar=2_000)
    assert not should_compact(RunUsage(input_tokens=2_000), s)
    assert should_compact(RunUsage(input_tokens=2_001), s)
    assert not should_compact(None, s)


async def test_quarta_mensagem_compacta_e_mantem_originais(client, usar_modelo, limiar, resumidor):
    vistas: list[list[ModelMessage]] = []
    usar_modelo(modelo_eco(vistas))
    uid, h = await usuario(client)
    cid = (await criar(client, h))["id"]

    textos = [f"meu nome é Ana. {LONGO}", f"gosto de xadrez. {LONGO}", f"terceira. {LONGO}", "qual meu nome?"]
    for t in textos:
        r = await client.post(f"/api/chat/{cid}", json=corpo(t), headers=h)
        assert r.status_code == 200, r.text

    # Turnos 1 a 3 não compactam: o anterior ainda estava abaixo do limiar ou não havia o que resumir.
    assert len(resumidor) == 1
    assert "meu nome é Ana" in resumidor[0]
    # O 4º turno vê o Resumo e os 2 últimos turnos literais, não o texto do 1º.
    quarto = conteudos(vistas[3])
    assert RESUMO in quarto
    assert "meu nome é Ana" not in quarto
    assert "gosto de xadrez" in quarto and "terceira" in quarto and "qual meu nome?" in quarto

    # Mensagens originais continuam no banco e na API.
    msgs = (await client.get(f"/api/conversations/{cid}/messages", headers=h)).json()
    assert [m["role"] for m in msgs] == ["user", "assistant"] * 4
    assert msgs[-1]["parts"][-1]["text"] == "resposta 4"

    # O Resumo cobre até o fim do 1º turno e foi feito no 4º: o separador vai antes da 4ª pergunta.
    corte = (await client.get(f"/api/chat/{cid}/compactacao", headers=h)).json()
    assert corte == {"ate_message_id": msgs[1]["id"], "turno_message_id": msgs[6]["id"]}

    [ev] = await eventos("compaction", user_id=uid)
    assert ev.payload["tokens_antes"] > 2_000
    assert 0 < ev.payload["tokens_depois"] < ev.payload["tokens_antes"]
    assert ev.model == MODELO_RESUMO
    async with SessionLocal() as s:
        modelos = (await s.scalars(select(CreditLedger.model).where(CreditLedger.user_id == uid))).all()
    assert modelos.count(MODELO_RESUMO) == 1


def chunks(sse: str) -> list[dict]:
    return [json.loads(l[6:]) for l in sse.splitlines() if l.startswith("data: {")]


async def test_stream_avisa_compactando_so_no_turno_que_compacta(client, usar_modelo, limiar, resumidor):
    usar_modelo(modelo_eco([]))
    _, h = await usuario(client)
    cid = (await criar(client, h))["id"]
    streams = []
    for t in [f"um. {LONGO}", f"dois. {LONGO}", f"três. {LONGO}", "quatro"]:
        r = await client.post(f"/api/chat/{cid}", json=corpo(t), headers=h)
        assert r.status_code == 200, r.text
        streams.append(chunks(r.text))

    for s in streams[:3]:
        assert not [c for c in s if c["type"] == "data-compactando"]
    tipos = [c["type"] for c in streams[3]]
    avisos = [c for c in streams[3] if c["type"] == "data-compactando"]
    # Logo depois do start, "rodando"; antes do 1º texto do modelo, a mesma parte vira "feita".
    assert tipos[0] == "start" and tipos[1] == "data-compactando"
    assert [a["data"] for a in avisos] == [{"feita": False}, {"feita": True}]
    assert {a["id"] for a in avisos} == {"compactacao"}
    assert tipos.index("data-compactando", 2) < tipos.index("text-start")


async def test_proximo_turno_usa_resumo_sem_resumir_de_novo(client, usar_modelo, limiar, resumidor, monkeypatch):
    vistas: list[list[ModelMessage]] = []
    usar_modelo(modelo_eco(vistas))
    _, h = await usuario(client)
    cid = (await criar(client, h))["id"]
    for t in [f"meu nome é Ana. {LONGO}", f"dois. {LONGO}", f"três. {LONGO}", "quatro"]:
        assert (await client.post(f"/api/chat/{cid}", json=corpo(t), headers=h)).status_code == 200
    monkeypatch.setattr(settings, "compactacao_limiar", 100_000)

    assert (await client.post(f"/api/chat/{cid}", json=corpo("cinco"), headers=h)).status_code == 200

    assert len(resumidor) == 1
    quinto = conteudos(vistas[4])
    assert RESUMO in quinto and "meu nome é Ana" not in quinto and "cinco" in quinto


async def test_abaixo_do_limiar_nao_compacta(client, usar_modelo, resumidor):
    usar_modelo(modelo_eco([]))
    _, h = await usuario(client)
    cid = (await criar(client, h))["id"]
    for t in ["um", "dois", "três", "quatro"]:
        assert (await client.post(f"/api/chat/{cid}", json=corpo(t), headers=h)).status_code == 200

    assert resumidor == []
    assert (await client.get(f"/api/chat/{cid}/compactacao", headers=h)).json() == {"ate_message_id": None, "turno_message_id": None}


def pares_orfaos(msgs: list[ModelMessage]) -> list[str]:
    """Ids de ToolReturnPart sem o ToolCallPart antes, na lista que o modelo recebeu."""
    chamadas: set[str] = set()
    orfaos = []
    for m in msgs:
        for p in m.parts:
            if isinstance(p, ToolCallPart):
                chamadas.add(p.tool_call_id)
            elif isinstance(p, ToolReturnPart) and p.tool_call_id not in chamadas:
                orfaos.append(p.tool_call_id)
    return orfaos


async def test_resumo_nao_corta_entre_tool_call_e_resultado(client, usar_modelo, usar_rotas, limiar, resumidor):
    usar_rotas(Rotas())
    vistas: list[list[ModelMessage]] = []

    # Todo turno chama web_search no 1º request e responde texto longo no 2º.
    async def stream(msgs: list[ModelMessage], info: AgentInfo):
        vistas.append(msgs)
        ultimo = msgs[-1]
        if isinstance(ultimo, ModelRequest) and any(isinstance(p, UserPromptPart) for p in ultimo.parts):
            yield {0: DeltaToolCall(name="web_search", json_args=json.dumps({"query": "x"}), tool_call_id=f"c{len(vistas)}")}
            return
        yield f"resposta {LONGO}"

    usar_modelo(ComUso(stream_function=stream, model_name=MODELO))
    _, h = await usuario(client)
    cid = (await criar(client, h))["id"]

    for t in ["um", "dois", "três", "quatro", "cinco"]:
        assert (await client.post(f"/api/chat/{cid}", json=corpo(t), headers=h)).status_code == 200

    assert len(resumidor) >= 1
    for msgs in vistas:
        assert pares_orfaos(msgs) == []
    # Cada chamada que sobrou literal tem o retorno junto, e a última vista ainda tem tool.
    assert any(isinstance(p, ToolReturnPart) for m in vistas[-1] for p in m.parts)
