"""Retry com backoff e jitter, fallback de modelo e registro do turno (ADR 0012)."""

import asyncio
import time
from collections.abc import AsyncGenerator
from contextlib import AsyncExitStack, asynccontextmanager
from dataclasses import dataclass, field
from typing import Any

import httpx
import httpx2
from pydantic_ai.exceptions import FallbackExceptionGroup, ModelAPIError, ModelHTTPError
from pydantic_ai.models import Model, StreamedResponse
from pydantic_ai.models.fallback import FallbackModel
from pydantic_ai.models.wrapper import WrapperModel
from tenacity import AsyncRetrying, RetryCallState, retry_if_exception, stop_after_attempt, wait_exponential_jitter

TENTATIVAS = 3
STATUS_TRANSITORIOS = {429, 500, 502, 503, 504}
TIMEOUTS = (TimeoutError, httpx.TimeoutException, httpx2.TimeoutException)
# O que o chat trata como falha do provedor: 502 antes do stream, chunk de erro depois.
ERROS_PROVEDOR = (ModelAPIError, FallbackExceptionGroup, *TIMEOUTS)
ESPERA_MAX_S = 10.0
_jitter = wait_exponential_jitter(initial=1, max=ESPERA_MAX_S)


async def dormir(segundos: float) -> None:
    """Pausa entre tentativas. Os testes trocam por no-op."""
    await asyncio.sleep(segundos)


# REVISAR(human): o que é erro transitório (ADR 0012). 429 e 5xx de gateway repetem.
# Outro 4xx é erro do request: repetir ou trocar de modelo só gasta. Timeout e erro
# de API sem status (conexão) repetem. A mesma regra decide o retry e o fallback.
def transitorio(exc: BaseException) -> bool:
    if isinstance(exc, ModelHTTPError):
        return exc.status_code in STATUS_TRANSITORIOS
    return isinstance(exc, (ModelAPIError, *TIMEOUTS))


def _espera(estado: RetryCallState) -> float:
    """Retry-After do provedor quando vem; senão exponencial com jitter."""
    exc = estado.outcome.exception() if estado.outcome else None
    pedido = getattr(exc, "retry_after", None)
    return min(pedido, ESPERA_MAX_S) if pedido else _jitter(estado)


def causa(exc: BaseException) -> BaseException:
    """Último erro real. FallbackExceptionGroup junta um por modelo."""
    while isinstance(exc, BaseExceptionGroup) and exc.exceptions:
        exc = exc.exceptions[-1]
    return exc


def resumo_erro(exc: BaseException) -> dict[str, Any]:
    exc = causa(exc)
    return {"erro": type(exc).__name__, "status": getattr(exc, "status_code", None), "msg": str(exc)[:500]}


@dataclass
class Turno:
    """O que aconteceu com o modelo num turno. Vira `llm_retry`, `llm_fallback` e o payload do `llm_call`."""

    pedido: str
    t0: float = field(default_factory=time.perf_counter)
    tentativas: int = 0
    retries: list[dict[str, Any]] = field(default_factory=list)
    fallbacks: list[dict[str, Any]] = field(default_factory=list)
    respondido: str | None = None
    primeiro_token_ms: int | None = None
    _ultimo_erro: BaseException | None = None

    def marcar_primeiro_token(self) -> None:
        if self.primeiro_token_ms is None:
            self.primeiro_token_ms = int((time.perf_counter() - self.t0) * 1000)


class ComRetry(WrapperModel):
    """Repete a abertura do stream em erro transitório. Falha no meio do stream não repete."""

    def __init__(self, wrapped: Model, turno: Turno, anterior: str | None):
        super().__init__(wrapped)
        self.turno = turno
        self.anterior = anterior  # modelo antes deste na cadeia; None no primeiro

    def _antes_de_dormir(self, estado: RetryCallState) -> None:
        exc = estado.outcome.exception() if estado.outcome else None
        self.turno.retries.append(
            {"modelo": self.model_name, "tentativa": estado.attempt_number, **resumo_erro(exc)}
        )

    def _tentativas(self) -> AsyncRetrying:
        return AsyncRetrying(
            stop=stop_after_attempt(TENTATIVAS),
            wait=_espera,
            retry=retry_if_exception(transitorio),
            before_sleep=self._antes_de_dormir,
            sleep=lambda s: dormir(s),
            reraise=True,
        )

    @asynccontextmanager
    async def request_stream(self, messages, model_settings, model_request_parameters, run_context=None) -> AsyncGenerator[StreamedResponse]:
        t = self.turno
        # FallbackModel só chega aqui quando o anterior esgotou.
        if self.anterior:
            t.fallbacks.append({"de": self.anterior, "para": self.model_name, **resumo_erro(t._ultimo_erro or Exception())})
        async with AsyncExitStack() as pilha:
            try:
                async for tentativa in self._tentativas():
                    with tentativa:
                        t.tentativas += 1
                        stream = await pilha.enter_async_context(
                            self.wrapped.request_stream(messages, model_settings, model_request_parameters, run_context)
                        )
            except BaseException as exc:
                t._ultimo_erro = exc
                raise
            t.respondido = self.model_name
            # yield fora do retry: erro de quem consome o stream não repete o request.
            yield stream

    async def request(self, messages, model_settings, model_request_parameters):
        async for tentativa in self._tentativas():
            with tentativa:
                self.turno.tentativas += 1
                resposta = await self.wrapped.request(messages, model_settings, model_request_parameters)
        self.turno.respondido = self.model_name
        return resposta


def cadeia(turno: Turno, modelos: list[Model]) -> Model:
    """Cada modelo com retry próprio; FallbackModel troca para o próximo quando um esgota."""
    nomes = [None, *(m.model_name for m in modelos[:-1])]
    com_retry = [ComRetry(m, turno, a) for m, a in zip(modelos, nomes, strict=True)]
    if len(com_retry) == 1:
        return com_retry[0]
    return FallbackModel(*com_retry, fallback_on=transitorio)
