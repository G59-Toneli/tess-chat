"""Pontes das libs de auth do Google (google-auth, requests-oauthlib) para o transporte httpx injetável (ADR 0017).

Com as pontes, o `httpx.MockTransport` dos testes vê o POST em `/token` do refresh e do callback.
"""

import os

import httpx
import requests
from google.auth import transport
from google.auth.exceptions import TransportError
from requests.adapters import BaseAdapter
from requests.structures import CaseInsensitiveDict

# Sem isto, oauthlib levanta Warning quando o Google devolve escopo diferente do pedido: consentimento
# granular (usuário desmarca gmail.send) ou include_granted_scopes (escopo antigo volta junto).
os.environ.setdefault("OAUTHLIB_RELAX_TOKEN_SCOPE", "1")

TIMEOUT = 30.0


def _cliente(t: httpx.BaseTransport | None, timeout: float | None) -> httpx.Client:
    """Cliente síncrono: as libs do Google rodam em thread (asyncio.to_thread). MockTransport atende sync e async."""
    return httpx.Client(transport=t, timeout=timeout or TIMEOUT)


class _Resposta(transport.Response):
    def __init__(self, r: httpx.Response):
        self._r = r

    @property
    def status(self) -> int:
        return self._r.status_code

    @property
    def headers(self):
        return self._r.headers

    @property
    def data(self) -> bytes:
        return self._r.content


class RequestHttpx(transport.Request):
    """`google.auth.transport.Request` sobre httpx. Usado em `Credentials.refresh`."""

    def __init__(self, t: httpx.BaseTransport | None = None):
        self.t = t

    def __call__(self, url, method="GET", body=None, headers=None, timeout=None, **kwargs) -> _Resposta:
        try:
            with _cliente(self.t, timeout) as http:
                return _Resposta(http.request(method, url, content=body, headers=headers))
        except httpx.HTTPError as e:
            raise TransportError(e) from e


class AdaptadorRequests(BaseAdapter):
    """Adapter do `requests` sobre httpx. Montado no `OAuth2Session` do `Flow` quando há transporte injetado."""

    def __init__(self, t: httpx.BaseTransport):
        super().__init__()
        self.t = t

    def send(self, request, stream=False, timeout=None, verify=True, cert=None, proxies=None) -> requests.Response:
        segundos = timeout if isinstance(timeout, (int, float)) else None
        with _cliente(self.t, segundos) as http:
            r = http.request(request.method, request.url, content=request.body, headers=dict(request.headers))
        resp = requests.Response()
        resp.status_code = r.status_code
        resp.headers = CaseInsensitiveDict(r.headers)
        resp._content = r.content
        resp._content_consumed = True
        resp.encoding = r.encoding or "utf-8"
        resp.url = request.url
        resp.request = request
        return resp

    def close(self) -> None:
        pass
