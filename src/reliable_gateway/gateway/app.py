from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from uuid import uuid4

import httpx
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


def _invalid_parameter(request_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"error": "invalid_parameter", "request_id": request_id},
        headers={"X-Request-ID": request_id},
    )


def _request_id(request: Request) -> str:
    supplied_id = request.headers.get("X-Request-ID")
    if (
        supplied_id
        and len(supplied_id) <= 128
        and supplied_id.isascii()
        and supplied_id.isprintable()
    ):
        return supplied_id

    return str(uuid4())


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncIterator[None]:
    async with httpx.AsyncClient() as client:
        app.state.requests_client = client
        app.state.backend_index = 0
        app.state.backends = [
            ("a", "http://127.0.0.1:8081"),
            ("b", "http://127.0.0.1:8082"),
        ]
        yield


app = FastAPI(lifespan=lifespan)


@app.get("/v1/work")
async def work(request: Request) -> JSONResponse:
    request_id = _request_id(request)
    delay_raw = request.query_params.get("delay_ms", "0")
    fail = request.query_params.get("fail", "none")

    try:
        delay_ms = int(delay_raw)
    except (TypeError, ValueError):
        return _invalid_parameter(request_id)

    if not 0 <= delay_ms <= 2000 or fail not in {"none", "503", "timeout"}:
        return _invalid_parameter(request_id)

    state = request.app.state
    backend_id, backend_url = state.backends[state.backend_index]
    state.backend_index = (state.backend_index + 1) % len(state.backends)

    try:
        response = await state.requests_client.get(
            f"{backend_url}/v1/work",
            params={"delay_ms": delay_ms, "fail": fail},
            headers={"X-Request-ID": request_id},
        )
    except httpx.TimeoutException:
        # Timeout policy belongs to M2; do not misreport timeouts as 502.
        raise
    except httpx.TransportError:
        return JSONResponse(
            status_code=502,
            content={"error": "upstream_error", "request_id": request_id},
            headers={"X-Request-ID": request_id, "X-Backend-ID": backend_id},
        )
    return JSONResponse(
        status_code=response.status_code,
        content=response.json(),
        headers={"X-Request-ID": request_id, "X-Backend-ID": backend_id},
    )
