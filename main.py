from contextlib import asynccontextmanager

from fastapi import FastAPI

from src.rate_limiter.algorithms.leaky_bucket import LeakyBucketAlgorithm
from src.rate_limiter.middleware.middleware import HTTPRateLimiter


@asynccontextmanager
async def lifespan(app: FastAPI):
    await app.state.limiter.start()
    yield
    await app.state.limiter.stop()

app = FastAPI(lifespan=lifespan)

app.state.limiter = LeakyBucketAlgorithm(bucket_size=5, leak_rate=1)
app.add_middleware(HTTPRateLimiter, algorithm=app.state.limiter)

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/status")
async def status():
    return await app.state.limiter.get_status()
