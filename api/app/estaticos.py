"""Serve o build do front (web/dist) com fallback de SPA."""

from pathlib import Path

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse


def montar_estaticos(app: FastAPI, dist: Path) -> None:
    """Registra rota catch-all do front. Chame depois de todas as rotas da API."""
    if not (dist / "index.html").is_file():
        return
    raiz = dist.resolve()

    @app.get("/{caminho:path}", include_in_schema=False)
    async def front(caminho: str) -> FileResponse:
        # Rota de API que não casou é 404 de verdade, não HTML.
        if caminho == "api" or caminho.startswith("api/"):
            raise HTTPException(status_code=404)
        alvo = (raiz / caminho).resolve()
        if caminho and alvo.is_file() and alvo.is_relative_to(raiz):
            return FileResponse(alvo)
        return FileResponse(raiz / "index.html")
