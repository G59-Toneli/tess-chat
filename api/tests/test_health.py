async def test_health_responde_ok_com_banco_de_pe(client):
    resp = await client.get("/health")

    assert resp.status_code == 200
    assert resp.json() == {"status": "ok"}
