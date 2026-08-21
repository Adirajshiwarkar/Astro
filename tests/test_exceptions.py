import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient
from pydantic import BaseModel

from app.core.exceptions import NotFoundError, setup_exception_handlers
from app.core.middleware import CorrelationIdMiddleware


class DummyModel(BaseModel):
    name: str
    age: int


@pytest.mark.asyncio
async def test_exception_handling_pipeline() -> None:
    test_app = FastAPI()
    test_app.add_middleware(CorrelationIdMiddleware)
    setup_exception_handlers(test_app)

    @test_app.get("/error")
    async def trigger_app_error() -> None:
        raise NotFoundError("User not found")

    @test_app.get("/unhandled")
    async def trigger_unhandled() -> None:
        raise RuntimeError("Something went wrong internally")

    @test_app.post("/validate")
    async def trigger_validation(_data: DummyModel) -> dict[str, bool]:
        return {"ok": True}

    async with AsyncClient(
        transport=ASGITransport(app=test_app), base_url="http://test"
    ) as client:
        # 1. Test AppException (NotFoundError -> 404)
        resp = await client.get("/error")
        assert resp.status_code == 404
        data = resp.json()
        assert data["success"] is False
        assert data["error"]["message"] == "User not found"
        assert data["error"]["code"] == "NotFoundError"
        assert "correlation_id" in data
        assert resp.headers.get("X-Correlation-ID") == data["correlation_id"]

        # 2. Test Unhandled Exception (RuntimeError -> 500)
        resp = await client.get("/unhandled")
        assert resp.status_code == 500
        data = resp.json()
        assert data["success"] is False
        assert data["error"]["message"] == "An unexpected error occurred"
        assert data["error"]["code"] == "InternalServerError"

        # 3. Test Validation Error (Invalid schema -> 422)
        resp = await client.post(
            "/validate", json={"name": "Alice", "age": "not-a-number"}
        )
        assert resp.status_code == 422
        data = resp.json()
        assert data["success"] is False
        assert data["error"]["message"] == "Validation failed"
        assert data["error"]["code"] == "RequestValidationError"
        assert len(data["error"]["details"]) > 0
