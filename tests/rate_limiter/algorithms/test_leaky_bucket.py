import asyncio
from contextlib import asynccontextmanager
from time import time

import pytest
import pytest_asyncio
import respx
from fastapi import FastAPI
from httpx import ASGITransport
from httpx import AsyncClient

from rate_limiter.algorithms.leaky_bucket import LeakyBucketAlgorithm
from rate_limiter.core.request import RateLimitRequest
from rate_limiter.middleware.middleware import HTTPRateLimiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    await app.state.limiter.start()
    yield
    await app.state.limiter.stop()


@pytest_asyncio.fixture
async def app():
    """Fixture for the FastAPI application."""
    app = FastAPI(lifespan=lifespan)
    app.state.limiter = LeakyBucketAlgorithm(bucket_size=5, leak_rate=1)
    app.add_middleware(HTTPRateLimiter, algorithm=app.state.limiter)

    @app.get("/")
    async def root():
        return {"message": "Hello World"}

    return app


@pytest_asyncio.fixture
async def client(app):
    """Fixture for the FastAPI test client."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as ac:
        yield ac


@pytest_asyncio.fixture
async def leaky_bucket_algorithm():
    """Fixture for the LeakyBucketAlgorithm."""
    algorithm = LeakyBucketAlgorithm(bucket_size=5, leak_rate=1)
    await algorithm.start()
    yield algorithm
    await algorithm.stop()

@pytest.mark.asyncio
async def test_bucket_fills_correctly(leaky_bucket_algorithm):
    for i in range(5):
        request = RateLimitRequest(id=str(i), timestamp=time(), client_ip="127.0.0.1", path="/", method="GET")
        response = await leaky_bucket_algorithm.allow_request(request)
        assert response.is_allowed
    assert len(leaky_bucket_algorithm.bucket) == 5


@pytest.mark.asyncio
async def test_requests_processed_at_specified_rate(leaky_bucket_algorithm):
    for i in range(5):
        request = RateLimitRequest(id=str(i), timestamp=time(), client_ip="127.0.0.1", path="/", method="GET")
        await leaky_bucket_algorithm.allow_request(request)

    await asyncio.sleep(1.1)
    assert len(leaky_bucket_algorithm.bucket) == 4


@pytest.mark.asyncio
async def test_fifo_order_is_maintained(leaky_bucket_algorithm):
    for i in range(5):
        request = RateLimitRequest(id=str(i), timestamp=time(), client_ip="127.0.0.1", path="/", method="GET")
        await leaky_bucket_algorithm.allow_request(request)
    await asyncio.sleep(1.1)
    assert leaky_bucket_algorithm.bucket[0].id == "1"


@pytest.mark.asyncio
async def test_empty_bucket_behavior(leaky_bucket_algorithm):
    assert len(leaky_bucket_algorithm.bucket) == 0
    await asyncio.sleep(1.1)
    assert len(leaky_bucket_algorithm.bucket) == 0


@pytest.mark.asyncio
async def test_full_bucket_behavior(leaky_bucket_algorithm):
    for i in range(5):
        request = RateLimitRequest(id=str(i), timestamp=time(), client_ip="127.0.0.1", path="/", method="GET")
        response = await leaky_bucket_algorithm.allow_request(request)
        assert response.is_allowed

    request = RateLimitRequest(id="6", timestamp=time(), client_ip="127.0.0.1", path="/", method="GET")
    response = await leaky_bucket_algorithm.allow_request(request)
    assert not response.is_allowed


@pytest.mark.asyncio
async def test_concurrent_request_handling(leaky_bucket_algorithm):
    requests = [RateLimitRequest(id=str(i), timestamp=time(), client_ip="127.0.0.1", path="/", method="GET") for i in range(10)]
    responses = await asyncio.gather(*[leaky_bucket_algorithm.allow_request(req) for req in requests])
    accepted = [res for res in responses if res.is_allowed]
    rejected = [res for res in responses if not res.is_allowed]
    assert len(accepted) == 5
    assert len(rejected) == 5


@pytest.mark.asyncio
async def test_rate_limit_boundary_conditions(leaky_bucket_algorithm):
    for i in range(5):
        request = RateLimitRequest(id=str(i), timestamp=time(), client_ip="127.0.0.1", path="/", method="GET")
        await leaky_bucket_algorithm.allow_request(request)
    await asyncio.sleep(1.1)
    request = RateLimitRequest(id="6", timestamp=time(), client_ip="127.0.0.1", path="/", method="GET")
    response = await leaky_bucket_algorithm.allow_request(request)
    assert response.is_allowed


@respx.mock
@pytest.mark.asyncio
async def test_fastapi_middleware_integration(client):
    response = await client.get("/")
    assert response.status_code == 200
    assert "X-RateLimit-Limit" in response.headers


@respx.mock
@pytest.mark.asyncio
async def test_header_handling(client):
    response = await client.get("/")
    assert "X-RateLimit-Limit" in response.headers
    assert "X-RateLimit-Remaining" in response.headers


@respx.mock
@pytest.mark.asyncio
async def test_request_identification(client):
    response1 = await client.get("/", headers={"X-Forwarded-For": "127.0.0.1"})
    response2 = await client.get("/", headers={"X-Forwarded-For": "127.0.0.2"})
    assert "X-RateLimit-Remaining" in response1.headers
    assert "X-RateLimit-Remaining" in response2.headers
    assert response1.status_code == 200
    assert response2.status_code == 200
