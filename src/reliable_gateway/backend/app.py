import asyncio
from uuid import uuid4

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse


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


def _invalid_parameter(request_id: str) -> JSONResponse:
    return JSONResponse(
        status_code=400,
        content={"error": "invalid_parameter", "request_id": request_id},
        headers={"X-Request-ID": request_id},
    )


def create_app(backend_id: str) -> FastAPI:
    app = FastAPI()

    @app.get("/healthz")
    async def healthz() -> dict[str, str]:
        return {"status": "ok", "backend": backend_id}

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

        if fail == "503":
            return JSONResponse(
                status_code=503,
                content={
                    "error": "simulated_unavailable",
                    "request_id": request_id,
                },
                headers={"X-Request-ID": request_id},
            )

        if fail == "timeout":
            await asyncio.sleep(3)
        else:
            await asyncio.sleep(delay_ms / 1000)

        return JSONResponse(
            status_code=200,
            content={
                "backend": backend_id,
                "result": "ok",
                "request_id": request_id,
            },
            headers={"X-Request-ID": request_id},
        )

    return app
