import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_health_returns_200(client):
    response = await client.get("/api/v1/health")
    assert response.status_code == 200


async def test_health_returns_ok_status(client):
    response = await client.get("/api/v1/health")
    body = response.json()
    assert body["data"]["status"] == "ok"
    assert "meta" in body
