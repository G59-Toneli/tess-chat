"""Front estático servido pelo FastAPI com fallback de SPA."""

from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.estaticos import montar_estaticos


def _cliente(tmp_path: Path) -> TestClient:
    (tmp_path / "assets").mkdir()
    (tmp_path / "index.html").write_text("<html>app</html>")
    (tmp_path / "assets" / "x.js").write_text("console.log(1)")
    app = FastAPI()

    @app.get("/health")
    async def health() -> dict[str, str]:
        return {"status": "ok"}

    montar_estaticos(app, tmp_path)
    return TestClient(app)


def test_raiz_e_rota_do_front_devolvem_index(tmp_path: Path) -> None:
    c = _cliente(tmp_path)
    for rota in ("/", "/c/123", "/config"):
        r = c.get(rota)
        assert r.status_code == 200
        assert "app" in r.text
        assert r.headers["content-type"].startswith("text/html")


def test_asset_existente_e_servido(tmp_path: Path) -> None:
    r = _cliente(tmp_path).get("/assets/x.js")
    assert r.status_code == 200
    assert r.text == "console.log(1)"


def test_rota_de_api_continua_na_api(tmp_path: Path) -> None:
    c = _cliente(tmp_path)
    assert c.get("/health").json() == {"status": "ok"}
    assert c.get("/api/nao-existe").status_code == 404


def test_path_traversal_nao_sai_do_dist(tmp_path: Path) -> None:
    (tmp_path.parent / "segredo.txt").write_text("segredo")
    r = _cliente(tmp_path).get("/..%2Fsegredo.txt")
    assert "segredo" not in r.text


def test_sem_dist_nao_monta_nada(tmp_path: Path) -> None:
    app = FastAPI()
    montar_estaticos(app, tmp_path / "nao-existe")
    assert TestClient(app).get("/").status_code == 404
