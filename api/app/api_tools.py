"""Tool por API: o Usuário cadastra uma API HTTP como Tool, sem código (ticket 59, ADR 0024)."""

import json
import re
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from typing import Annotated, Any, Literal
from urllib.parse import quote, urlencode, urlsplit, urlunsplit

import httpx
from fastapi import APIRouter, Depends, HTTPException, Response
from pydantic import BaseModel, Field
from pydantic_ai import ModelRetry
from pydantic_ai import Tool as FerramentaAI
from sqlalchemy import DateTime, ForeignKey, Text, func, select
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Mapped, mapped_column

from app.audit import audit
from app.conectores import _cifrar, _decifrar
from app.conversas import Sessao, Usuario
from app.db import Base
from app.mcp import LIMITE_DESCRICAO_USUARIO, UrlRecusada, validar_url
from app.tools import LIMITE_CHARS_MCP, Tool, cortar, schema_para_modelo, transporte

TIMEOUT_S = 15
MAX_SALTOS = 3
# Começo do corpo que volta no erro, para o Usuário e para o modelo.
TRECHO_ERRO = 300
PLACEHOLDER = re.compile(r"\{([A-Za-z_][A-Za-z0-9_]*)\}")


class ApiTool(Base):
    __tablename__ = "api_tools"

    id: Mapped[uuid.UUID] = mapped_column(primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(ForeignKey("users.id", ondelete="CASCADE"))
    nome: Mapped[str] = mapped_column(Text)
    descricao: Mapped[str] = mapped_column(Text)
    metodo: Mapped[str] = mapped_column(Text)  # GET | POST
    url: Mapped[str] = mapped_column(Text)  # com placeholders {param}
    parametros: Mapped[list[dict[str, Any]]] = mapped_column(JSONB)
    corpo: Mapped[Any | None] = mapped_column(JSONB)  # template JSON, só no POST
    auth: Mapped[str] = mapped_column(Text)  # JSON {tipo, nome?, valor?, token?} cifrado com Fernet
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now())


# ---------- Definição ----------


class Parametro(BaseModel):
    nome: str = Field(pattern=r"^[A-Za-z_][A-Za-z0-9_]*$", max_length=40)
    tipo: Literal["string", "number", "integer", "boolean"] = "string"
    descricao: str = ""
    obrigatorio: bool = True


class Auth(BaseModel):
    tipo: Literal["nenhuma", "header", "bearer"] = "nenhuma"
    nome: str | None = None  # header
    valor: str | None = None  # header
    token: str | None = None  # bearer


class Definicao(BaseModel):
    nome: str = Field(pattern=r"^[a-z][a-z0-9_]*$", max_length=40)
    descricao: str = Field(min_length=1, max_length=1000)
    metodo: Literal["GET", "POST"] = "GET"
    url: str = Field(pattern=r"^https?://\S+$")
    parametros: list[Parametro] = []
    corpo: dict[str, Any] | list[Any] | None = None
    auth: Auth = Auth()


class ApiToolIn(Definicao):
    exemplo: dict[str, Any] = {}  # valores do request de teste


class ApiToolOut(BaseModel):
    id: uuid.UUID
    nome: str
    tool_nome: str
    descricao: str
    metodo: str
    url: str
    parametros: list[Parametro]
    corpo: dict[str, Any] | list[Any] | None
    auth_tipo: str
    created_at: datetime


class TesteOut(BaseModel):
    status: int
    corpo_cortado: str
    ms: int


class Invalida(ValueError):
    """Definição ou valor fora da regra. A mensagem vai para o Usuário (422) ou para o modelo."""


class Falha(Exception):
    """A API não respondeu: rede, timeout, redirect demais. A mensagem vai para o Usuário (502) ou para o modelo."""


def _nomes_no_corpo(v: Any) -> set[str]:
    if isinstance(v, dict):
        return set().union(*(_nomes_no_corpo(x) for x in v.values()))
    if isinstance(v, list):
        return set().union(*(_nomes_no_corpo(x) for x in v))
    return set(PLACEHOLDER.findall(v)) if isinstance(v, str) else set()


# regras da definição, checadas antes de qualquer request.
# Placeholder só no caminho e na query: no host, o valor mudaria o destino e furaria o SSRF.
# Todo {param} precisa estar em `parametros`; todo obrigatório precisa aparecer na URL ou no
# corpo (opcional não usado vira query string). Corpo só no POST. Auth completo ou nenhum.
def checar(d: Definicao) -> None:
    nomes = [p.nome for p in d.parametros]
    if len(set(nomes)) != len(nomes):
        raise Invalida("Há parâmetros com o mesmo nome.")
    partes = urlsplit(d.url)
    if PLACEHOLDER.search(partes.netloc):
        raise Invalida("Placeholder só pode ir no caminho ou na query da URL, não no host.")
    if d.corpo is not None and d.metodo != "POST":
        raise Invalida("Corpo só vale no método POST.")
    usados = set(PLACEHOLDER.findall(partes.path + partes.query)) | _nomes_no_corpo(d.corpo)
    if faltam := usados - set(nomes):
        raise Invalida(f"Placeholder sem parâmetro: {', '.join(sorted(faltam))}.")
    if soltos := [p.nome for p in d.parametros if p.obrigatorio and p.nome not in usados]:
        raise Invalida(f"Parâmetro obrigatório fora da URL e do corpo: {', '.join(soltos)}.")
    a = d.auth
    if a.tipo == "header" and not (a.nome and a.valor):
        raise Invalida("Auth por header precisa de nome e valor.")
    if a.tipo == "bearer" and not a.token:
        raise Invalida("Auth bearer precisa do token.")


def schema(d: Definicao) -> dict[str, Any]:
    """JSON Schema que o modelo recebe, montado dos parâmetros."""
    props = {p.nome: {"type": p.tipo, **({"description": p.descricao} if p.descricao else {})} for p in d.parametros}
    return {"type": "object", "properties": props, "required": [p.nome for p in d.parametros if p.obrigatorio]}


def _tipar(valor: Any, p: Parametro) -> Any:
    """Converte o valor para o tipo do parâmetro. Texto "3" num integer vira 3; o formulário manda texto."""
    erro = Invalida(f"O parâmetro {p.nome} precisa ser {p.tipo}.")
    if p.tipo == "string":
        return valor if isinstance(valor, str) else json.dumps(valor, ensure_ascii=False)
    if p.tipo == "boolean":
        if isinstance(valor, bool):
            return valor
        if isinstance(valor, str) and valor.strip().lower() in ("true", "false"):
            return valor.strip().lower() == "true"
        raise erro
    if isinstance(valor, bool):
        raise erro
    if isinstance(valor, str):
        try:
            valor = json.loads(valor.strip())
        except ValueError:
            raise erro from None
        if isinstance(valor, bool):
            raise erro
    if p.tipo == "integer" and isinstance(valor, float) and valor.is_integer():
        return int(valor)
    if isinstance(valor, int) or (p.tipo == "number" and isinstance(valor, float)):
        return valor
    raise erro


def argumentos(d: Definicao, args: dict[str, Any]) -> dict[str, Any]:
    """Valores tipados dos parâmetros. Faltar obrigatório é erro; opcional ausente fica de fora."""
    valores = {}
    for p in d.parametros:
        if args.get(p.nome) is None:
            if p.obrigatorio:
                raise Invalida(f"Falta o parâmetro obrigatório {p.nome}.")
            continue
        valores[p.nome] = _tipar(args[p.nome], p)
    return valores


# ---------- Execução ----------


def _texto(v: Any) -> str:
    return json.dumps(v) if isinstance(v, bool) else str(v)


def _corpo(v: Any, valores: dict[str, Any]) -> Any:
    if isinstance(v, dict):
        return {k: _corpo(x, valores) for k, x in v.items()}
    if isinstance(v, list):
        return [_corpo(x, valores) for x in v]
    if not isinstance(v, str):
        return v
    if m := PLACEHOLDER.fullmatch(v):
        return valores.get(m[1])  # "{n}" vira o valor tipado: number continua number
    return PLACEHOLDER.sub(lambda m: _texto(valores.get(m[1], "")), v)


# monta URL e corpo do request. Cada valor vai URL-encoded (quote com safe="")
# no caminho e na query: "a/b" vira "a%2Fb" e não cria segmento de rota; "?" não abre query.
# Só os placeholders mudam: o resto do template sai como o Usuário escreveu. Parâmetro que não
# aparece na URL nem no corpo entra no fim da query. Corpo: "{p}" sozinho vira o valor tipado;
# "{p}" dentro de texto vira texto.
def montar(d: Definicao, valores: dict[str, Any]) -> tuple[str, Any]:
    partes = urlsplit(d.url)

    def trocar(trecho: str) -> str:
        return PLACEHOLDER.sub(lambda m: quote(_texto(valores.get(m[1], "")), safe=""), trecho)

    usados = set(PLACEHOLDER.findall(partes.path + partes.query)) | _nomes_no_corpo(d.corpo)
    livres = urlencode([(k, _texto(v)) for k, v in valores.items() if k not in usados], quote_via=quote)
    query = "&".join(q for q in (trocar(partes.query), livres) if q)
    url = urlunsplit((partes.scheme, partes.netloc, trocar(partes.path), query, ""))
    return url, (_corpo(d.corpo, valores) if d.corpo is not None else None)


def _cabecalhos(auth: dict[str, Any]) -> dict[str, str]:
    if auth.get("tipo") == "header":
        return {auth["nome"]: auth["valor"]}
    if auth.get("tipo") == "bearer":
        return {"Authorization": f"Bearer {auth['token']}"}
    return {}


async def _validar(url: str) -> None:
    """validar_url do MCP, com o texto falando de API."""
    try:
        await validar_url(url)
    except UrlRecusada as e:
        raise UrlRecusada(str(e).replace("do servidor MCP", "da API").replace("um servidor MCP público", "uma API pública")) from e


def _legivel(r: httpx.Response) -> str:
    """JSON sai compacto; o resto sai cru. Os dois com o teto das tools MCP."""
    try:
        texto = json.dumps(r.json(), ensure_ascii=False, separators=(",", ":"))
    except ValueError:
        texto = r.text
    return cortar(texto, LIMITE_CHARS_MCP)


@dataclass
class Resposta:
    status: int
    texto: str
    ms: int

    @property
    def ok(self) -> bool:
        return 200 <= self.status < 300

    def erro(self) -> str:
        return f"A API respondeu {self.status}: {self.texto[:TRECHO_ERRO]}"


# SSRF igual ao web_fetch. validar_url roda na URL final, já com os valores, e em
# cada salto de redirect (até MAX_SALTOS, seguido à mão). O valor de auth só vai no header, nunca
# em log nem em Evento. Ressalva: o httpx resolve o DNS de novo (rebinding não coberto).
async def executar(
    d: Definicao, auth: dict[str, Any], valores: dict[str, Any], t: httpx.AsyncBaseTransport | None
) -> Resposta:
    url, corpo = montar(d, valores)
    await _validar(url)
    t0 = time.perf_counter()
    async with httpx.AsyncClient(transport=t, timeout=TIMEOUT_S) as http:
        req = http.build_request(d.metodo, url, json=corpo, headers=_cabecalhos(auth))
        try:
            for _ in range(MAX_SALTOS + 1):
                r = await http.send(req)
                if r.next_request is None:
                    break
                req = r.next_request
                await _validar(str(req.url))
            else:
                raise Falha(f"A API redirecionou mais de {MAX_SALTOS} vezes.")
        except httpx.TimeoutException as e:
            raise Falha(f"A API não respondeu em {TIMEOUT_S} s.") from e
        except httpx.HTTPError as e:
            raise Falha(f"Não foi possível conectar à API ({type(e).__name__}).") from e
    return Resposta(r.status_code, _legivel(r), int((time.perf_counter() - t0) * 1000))


# ---------- Turno ----------


def nome_da_tool(linha: ApiTool) -> str:
    """Nome no registro: único entre Usuários e dentro do limite do Gemini (40 + 9 < 64)."""
    return f"api_{linha.id.hex[:4]}_{linha.nome}"


def _definicao(linha: ApiTool) -> Definicao:
    return Definicao.model_validate(
        {k: getattr(linha, k) for k in ("nome", "descricao", "metodo", "url", "parametros", "corpo")}
    )


def ligar(linha: ApiTool, tool: Tool, t: httpx.AsyncBaseTransport | None) -> FerramentaAI[Any]:
    """Tool do turno. Status fora de 2xx e falha de rede voltam como texto ao modelo, sem quebrar o turno."""
    d = _definicao(linha)

    async def chamar(**args: Any) -> str:
        try:
            valores = argumentos(d, args)
        except Invalida as e:
            raise ModelRetry(str(e)) from e
        try:
            r = await executar(d, _decifrar(linha.auth), valores, t)
        except (UrlRecusada, Falha) as e:
            return f"A chamada à API falhou: {e}"
        return r.texto if r.ok else r.erro()

    return FerramentaAI.from_schema(chamar, tool.nome, tool.descricao, schema_para_modelo(tool.schema))


# ---------- API ----------

router = APIRouter(prefix="/api/api-tools", tags=["api-tools"])
Transporte = Annotated[httpx.AsyncBaseTransport | None, Depends(transporte)]

MODELOS = [
    ApiToolIn(
        nome="viacep",
        descricao="Consulta o endereço (logradouro, bairro, cidade, UF) de um CEP brasileiro.",
        url="https://viacep.com.br/ws/{cep}/json/",
        parametros=[Parametro(nome="cep", descricao="CEP com 8 dígitos, só números")],
        exemplo={"cep": "01001000"},
    ),
    ApiToolIn(
        nome="open_meteo",
        descricao="Temperatura atual e código do tempo (WMO) numa latitude e longitude.",
        url="https://api.open-meteo.com/v1/forecast?latitude={latitude}&longitude={longitude}&current=temperature_2m,weather_code",
        parametros=[
            Parametro(nome="latitude", tipo="number", descricao="Latitude em graus decimais"),
            Parametro(nome="longitude", tipo="number", descricao="Longitude em graus decimais"),
        ],
        exemplo={"latitude": -23.55, "longitude": -46.63},
    ),
    ApiToolIn(
        nome="cnpj",
        descricao="Dados públicos de uma empresa pelo CNPJ (razão social, situação, endereço, atividade).",
        url="https://brasilapi.com.br/api/cnpj/v1/{cnpj}",
        parametros=[Parametro(nome="cnpj", descricao="CNPJ com 14 dígitos, só números")],
        exemplo={"cnpj": "00000000000191"},
    ),
]


async def _testar(body: ApiToolIn, t: httpx.AsyncBaseTransport | None) -> Resposta:
    """Executa a definição com o exemplo. Regra ou URL recusada: 422. API fora do ar: 502."""
    try:
        checar(body)
        return await executar(body, body.auth.model_dump(), argumentos(body, body.exemplo), t)
    except (Invalida, UrlRecusada) as e:
        raise HTTPException(status_code=422, detail=str(e)) from e
    except Falha as e:
        raise HTTPException(status_code=502, detail=str(e)) from e


def _saida(linha: ApiTool) -> ApiToolOut:
    return ApiToolOut(
        id=linha.id,
        nome=linha.nome,
        tool_nome=nome_da_tool(linha),
        descricao=linha.descricao,
        metodo=linha.metodo,
        url=linha.url,
        parametros=[Parametro.model_validate(p) for p in linha.parametros],
        corpo=linha.corpo,
        auth_tipo=_decifrar(linha.auth).get("tipo", "nenhuma"),
        created_at=linha.created_at,
    )


@router.get("", response_model=list[ApiToolOut])
async def listar(session: Sessao, user: Usuario) -> list[ApiToolOut]:
    """Tools por API do Usuário. O valor de auth nunca volta."""
    q = select(ApiTool).where(ApiTool.user_id == user.id).order_by(ApiTool.created_at)
    return [_saida(x) for x in (await session.scalars(q)).all()]


@router.get("/modelos", response_model=list[ApiToolIn])
async def modelos(user: Usuario) -> list[ApiToolIn]:
    """Definições prontas, com exemplo, para a tela preencher o formulário."""
    return MODELOS


@router.post("/testar", response_model=TesteOut)
async def testar(body: ApiToolIn, user: Usuario, t: Transporte) -> TesteOut:
    """Executa o request com o exemplo e devolve o que o modelo receberia. Não grava."""
    r = await _testar(body, t)
    return TesteOut(status=r.status, corpo_cortado=r.texto, ms=r.ms)


# testar antes de salvar, como o cadastro de MCP. O request real com o exemplo
# roda ANTES de gravar; fora de 2xx vira 502 com status e começo do corpo, e nada fica no banco.
@router.post("", response_model=ApiToolOut, status_code=201)
async def cadastrar(body: ApiToolIn, session: Sessao, user: Usuario, t: Transporte) -> ApiToolOut:
    """Testa com o exemplo e grava a linha e a Tool com origem api."""
    r = await _testar(body, t)
    if not r.ok:
        raise HTTPException(status_code=502, detail=f"O teste com o exemplo falhou. {r.erro()}")
    linha = ApiTool(
        id=uuid.uuid4(),
        user_id=user.id,
        nome=body.nome,
        descricao=body.descricao.strip(),
        metodo=body.metodo,
        url=body.url,
        parametros=[p.model_dump() for p in body.parametros],
        corpo=body.corpo,
        auth=_cifrar(body.auth.model_dump(exclude_none=True)),
    )
    session.add(linha)
    try:
        await session.flush()  # a FK da Tool precisa da linha antes
    except IntegrityError as e:
        raise HTTPException(status_code=409, detail="Você já tem uma tool por API com esse nome") from e
    nome = nome_da_tool(linha)
    session.add(
        Tool(
            nome=nome,
            origem="api",
            descricao=linha.descricao,
            descricao_usuario=linha.descricao[:LIMITE_DESCRICAO_USUARIO],
            schema=schema(body),
            ativa_global=True,
            api_tool_id=linha.id,
        )
    )
    await audit(
        session,
        "api_tool_added",
        user_id=user.id,
        payload={"id": str(linha.id), "tool": nome, "metodo": linha.metodo, "url": linha.url, "auth_tipo": body.auth.tipo},
    )
    await session.commit()
    await session.refresh(linha)
    return _saida(linha)


@router.delete("/{aid}", status_code=204)
async def remover(aid: uuid.UUID, session: Sessao, user: Usuario) -> Response:
    """Apaga a linha. O cascade leva a Tool e os toggles por Conversa. Sem edição: remove e cadastra de novo."""
    linha = await session.get(ApiTool, aid)
    if linha is None or linha.user_id != user.id:
        raise HTTPException(status_code=404, detail="Tool por API inexistente")
    nome = nome_da_tool(linha)
    await session.delete(linha)
    await audit(session, "api_tool_removed", user_id=user.id, payload={"id": str(aid), "tool": nome})
    await session.commit()
    return Response(status_code=204)
