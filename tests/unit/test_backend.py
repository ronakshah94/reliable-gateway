from uuid import UUID

import httpx
import pytest

from reliable_gateway.backend.app import create_app


@pytest.mark.asyncio
async def test_healthz() -> None:
    transport = httpx.ASGITransport(app=create_app("a"))
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "backend": "a"}


@pytest.mark.asyncio
async def test_work_propagates_request_id() -> None:
    transport = httpx.ASGITransport(app=create_app("a"))
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.get(
            "/v1/work?delay_ms=0&fail=none",
            headers={"X-Request-ID": "request-123"},
        )

    assert response.status_code == 200
    assert response.headers["X-Request-ID"] == "request-123"
    assert response.json() == {
        "backend": "a",
        "result": "ok",
        "request_id": "request-123",
    }


@pytest.mark.asyncio
async def test_work_simulates_unavailable() -> None:
    transport = httpx.ASGITransport(app=create_app("a"))
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.get(
            "/v1/work?fail=503", headers={"X-Request-ID": "request-503"}
        )

    assert response.status_code == 503
    assert response.headers["X-Request-ID"] == "request-503"
    assert response.json() == {
        "error": "simulated_unavailable",
        "request_id": "request-503",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query",
    [
        "delay_ms=-1",
        "delay_ms=2001",
        "delay_ms=not-an-integer",
        "fail=invalid",
    ],
)
async def test_work_rejects_invalid_parameters(query: str) -> None:
    transport = httpx.ASGITransport(app=create_app("a"))
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.get(
            f"/v1/work?{query}", headers={"X-Request-ID": "request-invalid"}
        )

    assert response.status_code == 400
    assert response.headers["X-Request-ID"] == "request-invalid"
    assert response.json() == {
        "error": "invalid_parameter",
        "request_id": "request-invalid",
    }


@pytest.mark.asyncio
async def test_work_generates_request_id_when_header_is_missing() -> None:
    transport = httpx.ASGITransport(app=create_app("a"))
    async with httpx.AsyncClient(
        transport=transport, base_url="http://testserver"
    ) as client:
        response = await client.get("/v1/work")

    request_id = response.headers["X-Request-ID"]
    assert UUID(request_id).version == 4
    assert response.json()["request_id"] == request_id
