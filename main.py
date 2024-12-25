from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from src.rate_limiter.algorithms.leaky_bucket import LeakyBucketAlgorithm
from src.rate_limiter.core.request import RateLimitRequest
import time

from src.rate_limiter.middleware.middleware import HTTPRateLimiter

app = FastAPI()

limiter = LeakyBucketAlgorithm(bucket_size=5, leak_rate=1)
app.add_middleware(HTTPRateLimiter, algorithm=limiter)

@asynccontextmanager
async def lifespan(app: FastAPI):
    await limiter.start()
    yield
    await limiter.stop()


@app.get("/")
async def root(request: Request):
    rate_limit_request = RateLimitRequest(
        id=str(request.client.host),
        timestamp=time.time(),
        client_ip=request.client.host,
        path=request.url.path,
        method=request.method,
    )

    response = await limiter.allow_request(rate_limit_request)

    if not response.is_allowed:
        return JSONResponse(
            status_code=429,
            content={"error": "Too Many Requests"},
            headers=response.headers,
        )

    return {"message": "Hello World"}


@app.get("/status")
async def status():
    return await limiter.get_status()
