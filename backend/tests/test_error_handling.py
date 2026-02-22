import uuid

import pytest

pytestmark = pytest.mark.asyncio(loop_scope="session")


async def test_404_returns_error_format(client, trainer_for_api):
    """404s should use {"error": {"code": "...", "message": "..."}} format."""
    response = await client.get(f"/api/v1/clients/{uuid.uuid4()}")
    assert response.status_code == 404
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "http_404"
    assert "not found" in body["error"]["message"].lower()


async def test_422_validation_returns_error_format(client, trainer_for_api):
    """Pydantic validation errors should use the error format."""
    response = await client.post("/api/v1/clients", json={})
    assert response.status_code == 422
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "validation_error"
    assert "name" in body["error"]["message"].lower()


async def test_422_invalid_uuid_returns_error_format(client, trainer_for_api):
    """Invalid UUID path params should use the error format."""
    response = await client.get("/api/v1/clients/not-a-uuid")
    assert response.status_code == 422
    body = response.json()
    assert "error" in body
    assert body["error"]["code"] == "validation_error"


async def test_error_response_has_no_detail_key(client, trainer_for_api):
    """Error responses should NOT have a top-level 'detail' key."""
    response = await client.get(f"/api/v1/clients/{uuid.uuid4()}")
    assert response.status_code == 404
    body = response.json()
    assert "detail" not in body
