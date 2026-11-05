"""Gateway contract tests with in-memory inbound and mocked outbound HTTP.

These tests do not establish real-network, timeout, or disconnect behavior.
"""

from collections.abc import AsyncIterator
from uuid import UUID

import httpx
import pytest
import pytest_asyncio

from reliable_gateway.gateway.app import app


@pytest_asyncio.fixture
async def gateway(
    request: pytest.FixtureRequest,
) -> AsyncIterator[tuple[httpx.AsyncClient, list[httpx.Request]]]:
    calls: list[httpx.Request] = []
    error_type = getattr(request, "param", None)

    def upstream(request: httpx.Request) -> httpx.Response:
        calls.append(request)
        if error_type is not None:
            raise error_type("simulated upstream failure")
        request_id = request.headers["X-Request-ID"]
        if request.url.params["fail"] == "503":
            return httpx.Response(
                503,
                json={"error": "simulated_unavailable", "request_id": request_id},
            )
        backend_id = {8081: "a", 8082: "b"}[request.url.port]
        return httpx.Response(
            200,
            json={"backend": backend_id, "result": "ok", "request_id": request_id},
            headers={"Connection": "keep-alive", "X-Upstream-Private": "internal"},
        )

    # ASGITransport does not start lifespan; enter it explicitly for each test.
    async with app.router.lifespan_context(app):
        original_client = app.state.requests_client
        async with httpx.AsyncClient(
            transport=httpx.MockTransport(upstream)
        ) as outbound:
            app.state.requests_client = outbound
            try:
                async with httpx.AsyncClient(
                    transport=httpx.ASGITransport(app=app), base_url="http://gateway"
                ) as client:
                    yield client, calls
            finally:
                app.state.requests_client = original_client


@pytest.mark.asyncio
async def test_work_forwards_success_and_defaults(gateway) -> None:
    client, calls = gateway
    response = await client.get("/v1/work", headers={"X-Request-ID": "request-123"})

    assert len(calls) == 1
    assert calls[0].method == "GET"
    assert str(calls[0].url) == "http://127.0.0.1:8081/v1/work?delay_ms=0&fail=none"
    assert calls[0].headers["X-Request-ID"] == "request-123"
    assert response.status_code == 200
    assert response.headers["Content-Type"] == "application/json"
    assert response.headers["X-Backend-ID"] == "a"
    assert response.headers["X-Request-ID"] == "request-123"
    assert response.json() == {
        "backend": "a",
        "result": "ok",
        "request_id": "request-123",
    }


@pytest.mark.asyncio
@pytest.mark.parametrize("delay_ms", [0, 20, 2000])
@pytest.mark.parametrize("fail", ["none", "503", "timeout"])
async def test_work_forwards_valid_parameters(
    gateway, delay_ms: int, fail: str
) -> None:
    client, calls = gateway
    await client.get("/v1/work", params={"delay_ms": delay_ms, "fail": fail})

    assert len(calls) == 1
    assert dict(calls[0].url.params) == {"delay_ms": str(delay_ms), "fail": fail}


@pytest.mark.asyncio
async def test_twenty_requests_alternate_backends(gateway) -> None:
    client, calls = gateway
    for expected_backend, expected_port in [("a", 8081), ("b", 8082)] * 10:
        response = await client.get("/v1/work")
        assert response.status_code == 200
        assert response.json()["backend"] == expected_backend
        assert response.headers["X-Backend-ID"] == expected_backend
        assert calls[-1].url.port == expected_port
    assert len(calls) == 20


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "query",
    [
        "delay_ms=-1",
        "delay_ms=2001",
        "delay_ms=99999",
        "delay_ms=abc",
        "delay_ms=1.5",
        "delay_ms=",
        "fail=invalid",
        "fail=",
    ],
)
async def test_invalid_parameters_do_not_contact_backend(gateway, query: str) -> None:
    client, calls = gateway
    response = await client.get(
        f"/v1/work?{query}", headers={"X-Request-ID": "bad-query"}
    )

    assert response.status_code == 400
    assert response.json() == {"error": "invalid_parameter", "request_id": "bad-query"}
    assert response.headers["X-Request-ID"] == "bad-query"
    assert "X-Backend-ID" not in response.headers
    assert calls == []


@pytest.mark.asyncio
@pytest.mark.parametrize("request_id", ["custom-id", "x" * 128, "id with spaces"])
async def test_valid_request_id_is_propagated(gateway, request_id: str) -> None:
    client, calls = gateway
    response = await client.get("/v1/work", headers={"X-Request-ID": request_id})

    assert calls[0].headers["X-Request-ID"] == request_id
    assert response.headers["X-Request-ID"] == request_id
    assert response.json()["request_id"] == request_id


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "supplied_id", [None, b"", b"x" * 129, b"bad\tid", b"\xc3\xa9"]
)
async def test_missing_or_invalid_request_id_is_replaced(gateway, supplied_id) -> None:
    client, calls = gateway
    headers = [] if supplied_id is None else [(b"X-Request-ID", supplied_id)]
    response = await client.get("/v1/work", headers=headers)

    request_id = response.headers["X-Request-ID"]
    assert UUID(request_id).version == 4
    assert calls[0].headers["X-Request-ID"] == request_id
    assert response.json()["request_id"] == request_id


@pytest.mark.asyncio
async def test_backend_503_is_passed_through_without_retry(gateway) -> None:
    client, calls = gateway
    for backend_id in ["a", "b"]:
        response = await client.get(
            "/v1/work?fail=503", headers={"X-Request-ID": "unavailable"}
        )
        assert response.status_code == 503
        assert response.json() == {
            "error": "simulated_unavailable",
            "request_id": "unavailable",
        }
        assert response.headers["X-Request-ID"] == "unavailable"
        assert response.headers["X-Backend-ID"] == backend_id
    assert len(calls) == 2


@pytest.mark.asyncio
@pytest.mark.parametrize(
    "gateway",
    [httpx.ConnectError, httpx.ReadError, httpx.WriteError, httpx.RemoteProtocolError],
    indirect=True,
)
@pytest.mark.parametrize("supplied_id", [None, "failed-request"])
async def test_transport_failure_returns_502_without_retry(
    gateway, supplied_id
) -> None:
    client, calls = gateway
    headers = {} if supplied_id is None else {"X-Request-ID": supplied_id}
    response = await client.get("/v1/work", headers=headers)

    request_id = response.headers["X-Request-ID"]
    if supplied_id is None:
        assert UUID(request_id).version == 4
    else:
        assert request_id == supplied_id
    assert response.status_code == 502
    assert response.headers["Content-Type"] == "application/json"
    assert response.json() == {"error": "upstream_error", "request_id": request_id}
    assert response.headers["X-Backend-ID"] == "a"
    assert len(calls) == 1
    assert calls[0].url.port == 8081
    assert calls[0].headers["X-Request-ID"] == request_id


@pytest.mark.asyncio
@pytest.mark.parametrize("gateway", [httpx.ReadTimeout, RuntimeError], indirect=True)
async def test_timeouts_and_programming_errors_are_not_converted_to_502(
    gateway,
) -> None:
    client, calls = gateway
    with pytest.raises((httpx.ReadTimeout, RuntimeError), match="simulated upstream"):
        await client.get("/v1/work")
    assert len(calls) == 1


@pytest.mark.asyncio
async def test_arbitrary_and_hop_by_hop_headers_are_not_forwarded(gateway) -> None:
    client, calls = gateway
    response = await client.get(
        "/v1/work",
        headers={
            "Authorization": "Bearer test-only",
            "X-Client-Private": "private",
            "Connection": "X-Client-Private",
        },
    )

    assert "Authorization" not in calls[0].headers
    assert "X-Client-Private" not in calls[0].headers
    # HTTPX may generate its own Connection header; the inbound value must not pass.
    assert calls[0].headers.get("Connection") != "X-Client-Private"
    assert "Connection" not in response.headers
    assert "X-Upstream-Private" not in response.headers


@pytest.mark.asyncio
async def test_lifespan_closes_shared_client_even_on_error() -> None:
    with pytest.raises(RuntimeError, match="simulated lifespan failure"):
        async with app.router.lifespan_context(app):
            client = app.state.requests_client
            assert isinstance(client, httpx.AsyncClient)
            assert not client.is_closed
            raise RuntimeError("simulated lifespan failure")

    assert client.is_closed
